from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import (
    ANALOG_PROFILE_BY_DG_NAME,
    ANALOG_PROFILE_BY_SERIAL,
    ANALOG_THRESHOLD_PROFILES,
)
from app.db import get_db
from app.schemas import DGAlarmStatusResponse
from app.services.alarm_service import get_alarm_status_by_dg
from app.services.live_service import get_latest_all

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DG_NAMES = {"DG#1", "DG#2", "DG#3", "ME-PORT", "ME-STBD"}


def _normalize_dg_name(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip().upper().replace(" ", "").replace("_", "-")
    if raw in {"DG1", "DG#1", "DG-1"}:
        return "DG#1"
    if raw in {"DG2", "DG#2", "DG-2"}:
        return "DG#2"
    if raw in {"DG3", "DG#3", "DG-3"}:
        return "DG#3"
    if raw == "ME-PORT":
        return "ME-PORT"
    if raw == "ME-STBD":
        return "ME-STBD"
    return value.strip() if isinstance(value, str) else None


def _condition_match(value: float | None, cond: dict | None) -> bool:
    if value is None or not cond:
        return False
    if "gt" in cond and not (value > cond["gt"]):
        return False
    if "gte" in cond and not (value >= cond["gte"]):
        return False
    if "lt" in cond and not (value < cond["lt"]):
        return False
    if "lte" in cond and not (value <= cond["lte"]):
        return False
    return True


def _pick_profile_key(serial: str | None, dg_name: str | None) -> str:
    if serial and serial in ANALOG_PROFILE_BY_SERIAL:
        return ANALOG_PROFILE_BY_SERIAL[serial]
    if dg_name and dg_name in ANALOG_PROFILE_BY_DG_NAME:
        return ANALOG_PROFILE_BY_DG_NAME[dg_name]
    return "default"


def _classify_status(value: float | None, rule: dict | None) -> str:
    if not rule:
        return "N/A"
    if _condition_match(value, rule.get("critical")):
        return "Critical"
    if _condition_match(value, rule.get("warning")):
        return "Warning"
    if _condition_match(value, rule.get("normal")):
        return "Normal"
    return "N/A"


def _is_dashboard_dg(dg_name: str | None) -> bool:
    normalized = _normalize_dg_name(dg_name)
    return normalized in DG_NAMES


def _infer_dg_from_label(label: str | None) -> str | None:
    if label is None:
        return None
    text = str(label).strip()
    candidates = (
        "DG#1",
        "DG#2",
        "DG#3",
        "ME-PORT",
        "ME-STBD",
        "ME_PORT",
        "ME_STBD",
    )
    for prefix in candidates:
        if text.startswith(prefix + " "):
            return _normalize_dg_name(prefix)
    return None


def _strip_dg_prefix(label: str | None, dg_name: str | None) -> str | None:
    if label is None:
        return None
    text = str(label).strip()
    normalized = _normalize_dg_name(dg_name)
    if not normalized:
        return text
    variants = {normalized}
    if normalized.startswith("DG#"):
        variants.add(normalized.replace("#", ""))
        variants.add(normalized.replace("#", "-"))
    if normalized in {"ME-PORT", "ME-STBD"}:
        variants.add(normalized.replace("-", "_"))
    for prefix in variants:
        if text.startswith(prefix + " "):
            return text[len(prefix) + 1 :].strip()
    return text


@router.get("/analog_lable_value")
def dashboard_analog_lable_value(db: Session = Depends(get_db)):
    rows = get_latest_all(db)
    result = []
    for r in rows:
        if (r.unit or "").strip().lower() == "on/off":
            continue
        normalized_dg = _normalize_dg_name(r.dg_name) or _infer_dg_from_label(r.label)
        if normalized_dg not in DG_NAMES:
            continue
        normalized_label = _strip_dg_prefix(r.label, normalized_dg)
        profile_key = _pick_profile_key(r.serial, normalized_dg)
        profile = ANALOG_THRESHOLD_PROFILES.get(profile_key, ANALOG_THRESHOLD_PROFILES["default"])
        rule = profile.get((normalized_label or "").strip())
        result.append(
            {
                "label": normalized_label,
                "value": r.value,
                "unit": r.unit,
                "dg_name": normalized_dg,
                "status": _classify_status(r.value, rule),
                "profile": profile_key,
                "thresholds": {
                    "normal": (rule or {}).get("normal"),
                    "warning": (rule or {}).get("warning"),
                    "critical": (rule or {}).get("critical"),
                },
            }
        )
    return result


@router.get("/analog_lable_value_ME")
def dashboard_analog_lable_value_me(db: Session = Depends(get_db)):
    rows = get_latest_all(db)
    result = []
    for r in rows:
        if (r.unit or "").strip().lower() == "on/off":
            continue
        normalized_dg = _normalize_dg_name(r.dg_name) or _infer_dg_from_label(r.label)
        if normalized_dg not in {"ME-PORT", "ME-STBD"}:
            continue
        normalized_label = _strip_dg_prefix(r.label, normalized_dg)
        profile_key = _pick_profile_key(r.serial, normalized_dg)
        profile = ANALOG_THRESHOLD_PROFILES.get(profile_key, ANALOG_THRESHOLD_PROFILES["default"])
        rule = profile.get((normalized_label or "").strip())
        result.append(
            {
                "label": normalized_label,
                "value": r.value,
                "unit": r.unit,
                "dg_name": normalized_dg,
                "status": _classify_status(r.value, rule),
                "profile": profile_key,
                "thresholds": {
                    "normal": (rule or {}).get("normal"),
                    "warning": (rule or {}).get("warning"),
                    "critical": (rule or {}).get("critical"),
                },
            }
        )
    return result


@router.get("/live_digital_value")
def dashboard_live_digital_value(db: Session = Depends(get_db)):
    rows = get_latest_all(db)
    return [
        {
            "addr": r.addr,
            "label": r.label,
            "value": r.value,
            "unit": r.unit,
            "dg_name": _normalize_dg_name(r.dg_name),
            "timestamp": r.timestamp,
        }
        for r in rows
        if (r.unit or "").strip().lower() == "on/off" and _is_dashboard_dg(r.dg_name)
    ]


@router.get("/dg_status", response_model=list[DGAlarmStatusResponse])
def dashboard_dg_status(db: Session = Depends(get_db)):
    return get_alarm_status_by_dg(db)
