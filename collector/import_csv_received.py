import argparse
import csv
import datetime as dt
import logging
import os
import shutil
import signal
import sqlite3
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RECEIVED_DIR = BASE_DIR / "data" / "csv_received"
ARCHIVED_DIR = BASE_DIR / "data" / "csv_archived"
DB_PATH = BASE_DIR / "data" / "live_engine_data.db"
DEFAULT_INTERVAL = int(os.getenv("CSV_IMPORT_INTERVAL", "5"))
DG_ORDER = {"DG#1": 1, "DG#2": 2, "DG#3": 3, "ME-PORT": 4, "ME-STBD": 5}
DG_PREFIXES = ("DG#1", "DG#2", "DG#3", "ME-PORT", "ME-STBD", "ME_PORT", "ME_STBD", "PMS")
DG_PREFIXES_NO_PMS = ("DG#1", "DG#2", "DG#3", "ME-PORT", "ME-STBD", "ME_PORT", "ME_STBD")


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=DELETE;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS live_engine_data (
            imo INTEGER,
            serial TEXT,
            dg_name TEXT,
            addr TEXT,
            label TEXT,
            timestamp DATETIME,
            val REAL,
            unit TEXT
        );
        """
    )
    conn.execute(
        """
        UPDATE live_engine_data
        SET dg_name = 'UNKNOWN'
        WHERE dg_name IS NULL OR TRIM(dg_name) = '';
        """
    )
    conn.execute("DROP INDEX IF EXISTS idx_live_engine_data_key;")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_live_engine_data_key
        ON live_engine_data (imo, serial, dg_name, addr);
        """
    )
    conn.commit()


def parse_row(row: list[str]) -> tuple | None:
    row = [col.strip() for col in row]
    if not row or all(col == "" for col in row):
        return None

    try:
        imo_val = int(float(row[0]))
    except Exception:
        return None

    if len(row) == 8:
        imo, serial, dg_name, addr, label, timestamp, val, unit = row
    elif len(row) >= 9:
        # Format like:
        # imo, serial, addr, label, ts1, ts2, val1, val2, unit, [source...]
        imo, serial, addr, label, ts1, ts2, val1, val2, unit = row[:9]
        timestamp = ts2 or ts1
        val = val2 or val1
        dg_name = ""
    else:
        return None

    label = str(label).strip()
    dg_name = str(dg_name).strip()

    if dg_name:
        if dg_name.upper() in {"ME_PORT", "ME_STBD"}:
            dg_name = dg_name.replace("_", "-")
        label_variants = {dg_name}
        if dg_name.upper().startswith("DG#"):
            label_variants.add(dg_name.replace("#", ""))
            label_variants.add(dg_name.replace("#", "-"))
        if dg_name.upper() in {"ME-PORT", "ME-STBD"}:
            label_variants.add(dg_name.replace("-", "_"))
        for prefix in label_variants:
            if label.startswith(prefix + " "):
                label = label[len(prefix) + 1 :].strip()
                break
        if dg_name.upper() == "PMS":
            for prefix in DG_PREFIXES_NO_PMS:
                if label.startswith(prefix + " "):
                    label = label[len(prefix) + 1 :].strip()
                    break
    else:
        for prefix in DG_PREFIXES:
            if label.startswith(prefix + " "):
                dg_name = prefix.replace("ME_PORT", "ME-PORT").replace("ME_STBD", "ME-STBD")
                label = label[len(prefix) + 1 :].strip()
                break

    if str(serial).strip() == "" or str(addr).strip() == "" or str(label).strip() == "":
        return None

    if dg_name == "":
        dg_name = "UNKNOWN"

    try:
        val_num = float(val) if str(val).strip() != "" else None
    except Exception:
        val_num = None

    return (imo_val, serial, dg_name, str(addr), label, timestamp, val_num, unit)


def _sort_key(row: tuple) -> tuple:
    dg_name = row[2]
    addr = row[3]
    addr_key = int(addr) if str(addr).isdigit() else addr
    return (DG_ORDER.get(dg_name, 99), row[1], addr_key)


def import_csv_file(path: Path, conn: sqlite3.Connection) -> int:
    parsed_rows: list[tuple] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        for row in reader:
            parsed = parse_row(row)
            if not parsed:
                continue
            parsed_rows.append(parsed)

    parsed_rows.sort(key=_sort_key)

    conn.executemany(
        """
        INSERT INTO live_engine_data (imo, serial, dg_name, addr, label, timestamp, val, unit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(imo, serial, dg_name, addr) DO UPDATE SET
            dg_name = excluded.dg_name,
            label = excluded.label,
            timestamp = excluded.timestamp,
            val = excluded.val,
            unit = excluded.unit
        WHERE excluded.timestamp > live_engine_data.timestamp;
        """,
        parsed_rows,
    )
    conn.commit()
    return len(parsed_rows)


def move_to_archived(path: Path) -> Path:
    ARCHIVED_DIR.mkdir(parents=True, exist_ok=True)
    destination = ARCHIVED_DIR / path.name
    if destination.exists():
        suffix = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = ARCHIVED_DIR / f"{path.stem}_{suffix}{path.suffix}"
    shutil.move(str(path), str(destination))
    return destination


def run_once() -> None:
    RECEIVED_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not RECEIVED_DIR.exists():
        logging.warning("Missing folder: %s", RECEIVED_DIR)
        return

    files = sorted(RECEIVED_DIR.glob("*.csv"))
    if not files:
        return
    import_targets = files
    if len(files) >= 2:
        newest = max(files, key=lambda p: p.stat().st_mtime)
        import_targets = [newest]

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        conn.execute("DELETE FROM live_engine_data;")
        conn.commit()
        for csv_file in import_targets:
            try:
                imported = import_csv_file(csv_file, conn)
                logging.info("Imported %s rows from %s", imported, csv_file.name)
            except Exception as exc:
                logging.exception("Failed to import %s: %s", csv_file.name, exc)
        for csv_file in files:
            try:
                archived_path = move_to_archived(csv_file)
                logging.info("Archived %s -> %s", csv_file.name, archived_path.name)
            except Exception as exc:
                logging.exception("Failed to archive %s: %s", csv_file.name, exc)
    finally:
        conn.close()


def run_watch(interval_seconds: int, stop_event: threading.Event) -> None:
    # Run forever as a service; keep looping even if a cycle fails.
    while not stop_event.is_set():
        try:
            run_once()
        except Exception as exc:
            logging.exception("Unexpected error in run loop: %s", exc)
        # Wait with interruption support for clean shutdown.
        stop_event.wait(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import CSV files from data/csv_received into live_engine_data.db"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single import cycle and exit.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help="Polling interval in seconds when running continuously.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.once:
        run_once()
        return

    stop_event = threading.Event()

    def _handle_stop(signum, frame) -> None:
        logging.info("Stopping on signal %s", signum)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_stop)
        except Exception:
            # Some environments don't support all signals (e.g. Windows SIGTERM).
            pass

    run_watch(args.interval, stop_event)


if __name__ == "__main__":
    main()
