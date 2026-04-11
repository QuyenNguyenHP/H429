import argparse
import csv
import datetime as dt
import logging
import os
import shutil
import signal
import sqlite3
import threading
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RECEIVED_DIR = BASE_DIR / "csv_received"
ARCHIVED_DIR = BASE_DIR / "csv_archived"
DB_PATH = BASE_DIR / "live_engine_data.db"
DEFAULT_INTERVAL = int(os.getenv("CSV_IMPORT_INTERVAL", "5"))
DG_ORDER = {"DG#1": 1, "DG#2": 2, "DG#3": 3, "ME-PORT": 4, "ME-STBD": 5}
DG_PREFIXES = ("DG#1", "DG#2", "DG#3", "ME-PORT", "ME-STBD", "ME_PORT", "ME_STBD", "PMS")
DG_PREFIXES_NO_PMS = ("DG#1", "DG#2", "DG#3", "ME-PORT", "ME-STBD", "ME_PORT", "ME_STBD")


def normalize_dg_name(value: str) -> str:
    normalized = str(value).strip()
    if normalized.upper() in {"ME_PORT", "ME_STBD"}:
        normalized = normalized.replace("_", "-")
    return normalized


def split_dg_name_from_label(label: str) -> tuple[str, str]:
    normalized_label = str(label).strip()

    for prefix in DG_PREFIXES_NO_PMS:
        if normalized_label.startswith(prefix + " "):
            return normalize_dg_name(prefix), normalized_label[len(prefix) + 1 :].strip()

    if normalized_label.startswith("PMS "):
        remainder = normalized_label[len("PMS ") :].strip()
        for prefix in DG_PREFIXES_NO_PMS:
            if remainder.startswith(prefix + " "):
                return normalize_dg_name(prefix), remainder[len(prefix) + 1 :].strip()
        return "PMS", remainder

    return "", normalized_label


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

    if len(row) == 7:
        imo, serial, addr, label, timestamp, val, unit = row
        dg_name = ""
    elif len(row) == 8:
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
    dg_name = normalize_dg_name(str(dg_name).strip())

    # Keep PMS rows under the PMS group so they don't collide with DG rows on the same addr.
    if label.startswith("PMS "):
        if dg_name in {"", "PMS"}:
            dg_name = "PMS"
            label = label[len("PMS ") :].strip()
        else:
            detected_dg_name, stripped_label = split_dg_name_from_label(label)
            if detected_dg_name == dg_name:
                label = stripped_label
    if dg_name:
        if not label.startswith("PMS "):
            detected_dg_name, stripped_label = split_dg_name_from_label(label)
            if detected_dg_name == dg_name:
                label = stripped_label
            elif dg_name.upper() == "PMS":
                if label.startswith("PMS "):
                    label = label[len("PMS ") :].strip()
    else:
        if label.startswith("PMS "):
            dg_name = "PMS"
            label = label[len("PMS ") :].strip()
        else:
            dg_name, label = split_dg_name_from_label(label)

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


def read_parsed_rows(path: Path) -> list[tuple]:
    parsed_rows: list[tuple] = []
    non_empty_rows = 0
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if row and any(str(col).strip() for col in row):
                non_empty_rows += 1
            parsed = parse_row(row)
            if not parsed:
                continue
            parsed_rows.append(parsed)

    if non_empty_rows > 0 and not parsed_rows:
        raise ValueError(f"No importable rows found in {path.name}")

    parsed_rows.sort(key=_sort_key)
    return parsed_rows


def import_csv_file(path: Path, conn: sqlite3.Connection, replace_existing: bool = False) -> int:
    parsed_rows = read_parsed_rows(path)

    if replace_existing:
        conn.execute("DELETE FROM live_engine_data;")

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


def list_received_data_files() -> list[Path]:
    csv_files = list(RECEIVED_DIR.glob("*.csv"))
    zip_files = list(RECEIVED_DIR.glob("*.zip"))
    return [p for p in [*csv_files, *zip_files] if p.is_file()]


def extract_csv_from_zip(zip_path: Path) -> Path:
    extracted_dir = RECEIVED_DIR / "_tmp_extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_members = [info for info in zf.infolist() if not info.is_dir() and info.filename.lower().endswith(".csv")]
        if not csv_members:
            raise ValueError(f"No CSV file found inside zip: {zip_path.name}")

        newest_member = max(csv_members, key=lambda info: info.date_time)
        extracted_path = Path(zf.extract(newest_member, path=extracted_dir))
    return extracted_path


def cleanup_received_dir() -> None:
    for pattern in ("*.csv", "*.zip"):
        for path in RECEIVED_DIR.glob(pattern):
            if not path.is_file():
                continue
            try:
                path.unlink()
                logging.info("Deleted leftover file: %s", path.name)
            except Exception as exc:
                logging.exception("Failed to delete %s: %s", path.name, exc)


def cleanup_extracted_tmp_dir() -> None:
    extracted_dir = RECEIVED_DIR / "_tmp_extracted"
    if extracted_dir.exists():
        try:
            shutil.rmtree(extracted_dir)
        except Exception as exc:
            logging.exception("Failed to cleanup temp extraction dir %s: %s", extracted_dir, exc)


def run_once() -> None:
    RECEIVED_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not RECEIVED_DIR.exists():
        logging.warning("Missing folder: %s", RECEIVED_DIR)
        return

    files = list_received_data_files()
    if not files:
        return

    newest = max(files, key=lambda p: p.stat().st_mtime)
    logging.info("Selected newest file: %s", newest.name)

    conn = sqlite3.connect(DB_PATH)
    import_source: Path | None = None
    import_csv_path: Path | None = None
    import_and_archive_ok = False
    try:
        ensure_schema(conn)
        import_source = newest
        if newest.suffix.lower() == ".zip":
            import_csv_path = extract_csv_from_zip(newest)
            logging.info("Extracted CSV %s from %s", import_csv_path.name, newest.name)
        else:
            import_csv_path = newest

        imported = import_csv_file(import_csv_path, conn, replace_existing=True)
        logging.info("Imported %s rows from %s", imported, import_csv_path.name)

        archived_path = move_to_archived(import_source)
        logging.info("Archived %s -> %s", import_source.name, archived_path.name)
        import_and_archive_ok = True
    finally:
        conn.close()
        if import_and_archive_ok:
            cleanup_received_dir()
        cleanup_extracted_tmp_dir()


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
        description="Import CSV files from collector/csv_received into collector/live_engine_data.db"
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
