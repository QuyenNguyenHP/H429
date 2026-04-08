import argparse
import csv
import datetime as dt
import os
import shutil
import sqlite3
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RECEIVED_DIR = BASE_DIR / "data" / "csv_received"
ARCHIVED_DIR = BASE_DIR / "data" / "csv_archived"
DB_PATH = BASE_DIR / "data" / "live_engine_data.db"


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
        CREATE UNIQUE INDEX IF NOT EXISTS idx_live_engine_data_key
        ON live_engine_data (imo, serial, addr);
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

    # Normalize dg_name from label prefix for 6 machine types.
    label = str(label).strip()
    prefixes = ("DG#1", "DG#2", "DG#3", "ME_PORT", "ME_STBD", "PMS")
    for prefix in prefixes:
        if label.startswith(prefix + " "):
            dg_name = prefix
            label = label[len(prefix) + 1 :].strip()
            break

    if str(serial).strip() == "" or str(addr).strip() == "" or str(label).strip() == "":
        return None

    try:
        val_num = float(val) if str(val).strip() != "" else None
    except Exception:
        val_num = None

    return (imo_val, serial, dg_name, str(addr), label, timestamp, val_num, unit)


def import_csv_file(path: Path, conn: sqlite3.Connection) -> int:
    imported = 0
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        for row in reader:
            parsed = parse_row(row)
            if not parsed:
                continue
            conn.execute(
                """
                INSERT INTO live_engine_data (imo, serial, dg_name, addr, label, timestamp, val, unit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(imo, serial, addr) DO UPDATE SET
                    dg_name = excluded.dg_name,
                    label = excluded.label,
                    timestamp = excluded.timestamp,
                    val = excluded.val,
                    unit = excluded.unit;
                """,
                parsed,
            )
            imported += 1
    conn.commit()
    return imported


def move_to_archived(path: Path) -> Path:
    ARCHIVED_DIR.mkdir(parents=True, exist_ok=True)
    destination = ARCHIVED_DIR / path.name
    if destination.exists():
        suffix = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = ARCHIVED_DIR / f"{path.stem}_{suffix}{path.suffix}"
    shutil.move(str(path), str(destination))
    return destination


def run_once() -> None:
    if not RECEIVED_DIR.exists():
        print(f"Missing folder: {RECEIVED_DIR}")
        return

    files = sorted(RECEIVED_DIR.glob("*.csv"))
    if not files:
        print("No CSV files found.")
        return
    import_targets = files
    if len(files) >= 2:
        newest = max(files, key=lambda p: p.stat().st_mtime)
        import_targets = [newest]

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        for csv_file in import_targets:
            try:
                imported = import_csv_file(csv_file, conn)
                print(f"Imported {imported} rows from {csv_file.name}")
            except Exception as exc:
                print(f"Failed to import {csv_file.name}: {exc}")
        for csv_file in files:
            try:
                archived_path = move_to_archived(csv_file)
                print(f"Archived {csv_file.name} -> {archived_path.name}")
            except Exception as exc:
                print(f"Failed to archive {csv_file.name}: {exc}")
    finally:
        conn.close()


def run_watch(interval_seconds: int) -> None:
    while True:
        run_once()
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import CSV files from data/csv_received into live_engine_data.db"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep watching the folder and import new CSV files.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("CSV_IMPORT_INTERVAL", "5")),
        help="Polling interval in seconds when using --watch.",
    )
    args = parser.parse_args()

    if args.watch:
        run_watch(args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
