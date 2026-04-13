import socket
import subprocess
import sys
import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import SystemHealthResponse, SystemStatusResponse
from app.services.system_service import get_health, get_status

router = APIRouter(prefix="/api/system", tags=["system"])
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "backend"
COLLECTOR_DIR = PROJECT_ROOT / "collector"
BACKEND_RUN_PATH = BACKEND_DIR / "run.py"
MODE1_SCRIPT_PATH = COLLECTOR_DIR / "mode1_import_data_from_drums.py"
MODE2_SCRIPT_PATH = COLLECTOR_DIR / "mode2_data_collector_from_database.py"
STATE_FILE_PATH = BACKEND_DIR / ".data_connection_state.json"
CONNECTION_FLAG_PATH = BACKEND_DIR / ".data_connection_enabled"

_backend_process: subprocess.Popen | None = None
_collector_process: subprocess.Popen | None = None
_collector_mode: str | None = None
_collector_script: str | None = None
BACKEND_PORT = 8131


def _is_process_running(proc: subprocess.Popen | None) -> bool:
    return proc is not None and proc.poll() is None


def _is_pid_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def _save_state(mode: str | None, script_path: str | None, pid: int | None) -> None:
    payload = {"mode": mode, "collector_script": script_path, "collector_pid": pid}
    STATE_FILE_PATH.write_text(json.dumps(payload), encoding="utf-8")


def _load_state() -> dict:
    if not STATE_FILE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_FILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _clear_state() -> None:
    try:
        if STATE_FILE_PATH.exists():
            STATE_FILE_PATH.unlink()
    except Exception:
        pass


def _set_connection_enabled(enabled: bool) -> None:
    if enabled:
        CONNECTION_FLAG_PATH.write_text("1\n", encoding="utf-8")
        return
    try:
        if CONNECTION_FLAG_PATH.exists():
            CONNECTION_FLAG_PATH.unlink()
    except Exception:
        pass


def _is_port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _spawn_python(script_path: Path, cwd: Path) -> subprocess.Popen:
    if not script_path.exists():
        raise HTTPException(status_code=500, detail=f"Script not found: {script_path}")

    kwargs = {
        "args": [sys.executable, str(script_path)],
        "cwd": str(cwd),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if sys.platform.startswith("win"):
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    return subprocess.Popen(**kwargs)


def _stop_process(proc: subprocess.Popen | None) -> None:
    if not _is_process_running(proc):
        return
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


@router.get("/health", response_model=SystemHealthResponse)
def health(db: Session = Depends(get_db)):
    return get_health(db)


@router.get("/status", response_model=SystemStatusResponse)
def status(db: Session = Depends(get_db)):
    return get_status(db)


@router.get("/data_connection/status")
def data_connection_status():
    backend_running = _is_port_open("127.0.0.1", BACKEND_PORT) or _is_process_running(_backend_process)
    collector_running = _is_process_running(_collector_process)
    mode = _collector_mode if collector_running else None
    script = _collector_script if collector_running else None

    if not collector_running:
        state = _load_state()
        state_pid = state.get("collector_pid")
        if _is_pid_running(state_pid):
            collector_running = True
            mode = state.get("mode")
            script = state.get("collector_script")
        else:
            _clear_state()

    connected = backend_running and collector_running
    return {
        "connected": connected,
        "backend_running": backend_running,
        "collector_running": collector_running,
        "mode": mode,
        "collector_script": script,
    }


@router.post("/data_connection/connect")
def data_connection_connect(payload: dict):
    global _backend_process, _collector_process, _collector_mode, _collector_script

    mode_raw = str(payload.get("mode", "")).strip().lower().replace(" ", "")
    mode = "mode1" if mode_raw in {"mode1", "1"} else "mode2" if mode_raw in {"mode2", "2"} else None
    if mode is None:
        raise HTTPException(status_code=400, detail="mode must be 'mode1' or 'mode2'")

    backend_running = _is_port_open("127.0.0.1", BACKEND_PORT) or _is_process_running(_backend_process)
    if not backend_running:
        _backend_process = _spawn_python(BACKEND_RUN_PATH, BACKEND_DIR)
        backend_running = True

    if _is_process_running(_collector_process) and _collector_mode != mode:
        _stop_process(_collector_process)
        _collector_process = None
        _collector_mode = None
        _collector_script = None

    if not _is_process_running(_collector_process):
        script_path = MODE1_SCRIPT_PATH if mode == "mode1" else MODE2_SCRIPT_PATH
        _collector_process = _spawn_python(script_path, COLLECTOR_DIR)
        _collector_mode = mode
        _collector_script = str(script_path)
        _save_state(_collector_mode, _collector_script, _collector_process.pid)
    _set_connection_enabled(True)

    collector_running = _is_process_running(_collector_process)
    return {
        "connected": backend_running and collector_running,
        "backend_running": backend_running,
        "collector_running": collector_running,
        "mode": _collector_mode,
        "collector_script": _collector_script,
        "button_text": "Disconnect" if (backend_running and collector_running) else "Connect",
    }


@router.post("/data_connection/disconnect")
def data_connection_disconnect():
    global _collector_process, _collector_mode, _collector_script

    _stop_process(_collector_process)

    if not _is_process_running(_collector_process):
        state = _load_state()
        state_pid = state.get("collector_pid")
        if _is_pid_running(state_pid):
            if sys.platform.startswith("win"):
                subprocess.run(["taskkill", "/PID", str(state_pid), "/T", "/F"], check=False)
            else:
                subprocess.run(["kill", "-TERM", str(state_pid)], check=False)

    _collector_process = None
    _collector_mode = None
    _collector_script = None
    _clear_state()
    _set_connection_enabled(False)

    backend_running = _is_port_open("127.0.0.1", BACKEND_PORT) or _is_process_running(_backend_process)
    return {
        "connected": False,
        "backend_running": backend_running,
        "collector_running": False,
        "mode": None,
        "collector_script": None,
        "button_text": "Connect",
    }
