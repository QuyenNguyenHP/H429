import argparse
import logging
import os
import signal
import sqlite3
import threading
from datetime import timedelta
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
SQLITE_DB_PATH = BASE_DIR / "live_engine_data.db"
CONNECTION_FLAG_PATH = BASE_DIR.parent / "backend" / ".data_connection_enabled"
DEFAULT_INTERVAL = int(os.getenv("DB_IMPORT_INTERVAL", "210"))

MYSQL_HOST = os.getenv("MYSQL_HOST", "146.235.17.60")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "admin")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "FB1bJ+EplTK8")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "Hardware_Test")
MYSQL_TABLE = os.getenv("MYSQL_TABLE", "H429")
DG_PREFIXES = ("DG#1", "DG#2", "DG#3", "ME-PORT", "ME-STBD", "ME_PORT", "ME_STBD")
DG_ORDER = {
    "DG#1": 1,
    "DG#2": 2,
    "DG#3": 3,
    "ME-PORT": 4,
    "ME-STBD": 5,
    "PMS": 6,
    "UNKNOWN": 99,
}


def is_data_connection_enabled() -> bool:
    if not CONNECTION_FLAG_PATH.exists():
        return True
    try:
        raw = CONNECTION_FLAG_PATH.read_text(encoding="utf-8").strip().lower()
        return raw in {"1", "true", "yes", "on", "connected"}
    except Exception:
        return True


def ensure_sqlite_schema(conn: sqlite3.Connection) -> None:
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
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_live_engine_data_key
        ON live_engine_data (imo, serial, dg_name, addr);
        """
    )
    conn.commit()


def normalize_dg_name(value: str) -> str:
    normalized = str(value).strip()
    if normalized.upper() in {"ME_PORT", "ME_STBD"}:
        normalized = normalized.replace("_", "-")
    return normalized


def split_dg_name_from_label(label: str) -> tuple[str, str]:
    normalized_label = str(label).strip()
    if normalized_label.startswith("PMS "):
        remainder = normalized_label[len("PMS ") :].strip()
        for prefix in DG_PREFIXES:
            if remainder.startswith(prefix + " "):
                # Keep PMS group; drop duplicated machine prefix in label.
                stripped_label = remainder[len(prefix) + 1 :].strip()
                return "PMS", stripped_label
        return "PMS", remainder

    if normalized_label == "PMS":
        return "PMS", ""

    for prefix in DG_PREFIXES:
        if normalized_label.startswith(prefix + " "):
            dg_name = normalize_dg_name(prefix)
            stripped_label = normalized_label[len(prefix) + 1 :].strip()
            return dg_name, stripped_label
    return "UNKNOWN", normalized_label


def _load_mysql_connector() -> Any:
    try:
        import pymysql  # type: ignore

        return ("pymysql", pymysql)
    except Exception:
        pass

    try:
        import mysql.connector  # type: ignore

        return ("mysql.connector", mysql.connector)
    except Exception:
        pass

    raise RuntimeError(
        "No MySQL driver found. Install one of: `pip install pymysql` or `pip install mysql-connector-python`."
    )


def fetch_latest_rows_from_mysql() -> tuple[Any, list[tuple]]:
    driver_name, driver = _load_mysql_connector()
    logging.info(
        "Connecting MySQL %s:%s db=%s table=%s via %s",
        MYSQL_HOST,
        MYSQL_PORT,
        MYSQL_DATABASE,
        MYSQL_TABLE,
        driver_name,
    )

    if driver_name == "pymysql":
        conn = driver.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=driver.cursors.Cursor,
        )
        placeholder = "%s"
    else:
        conn = driver.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
        )
        placeholder = "%s"

    try:
        cur = conn.cursor()
        max_query = f"SELECT MAX(`TimeStamp`) FROM `{MYSQL_TABLE}`"
        cur.execute(max_query)
        row = cur.fetchone()
        max_ts = row[0] if row else None

        if max_ts is None:
            logging.warning("Source table has no data.")
            return None, []

        prev_ts = max_ts - timedelta(seconds=1)
        data_query = (
            f"SELECT `IMO_no`, `SerialNo`, `ChannelNo`, `ChannelDescription`, `TimeStamp`, `Value`, `Unit` "
            f"FROM `{MYSQL_TABLE}` "
            f"WHERE `TimeStamp` = {placeholder} OR `TimeStamp` = {placeholder} "
            f"ORDER BY `TimeStamp`, `SerialNo`, `ChannelNo`"
        )
        cur.execute(data_query, (max_ts, prev_ts))
        rows = cur.fetchall()
        logging.info(
            "Fetched %s row(s) at TimeStamp in {%s, %s}",
            len(rows),
            max_ts,
            prev_ts,
        )
        return max_ts, rows
    finally:
        conn.close()


def normalize_sqlite_rows(mysql_rows: list[tuple]) -> list[tuple]:
    normalized: list[tuple] = []
    for row in mysql_rows:
        imo_no, serial_no, channel_no, channel_description, ts, value, unit = row
        try:
            imo_val = int(float(imo_no)) if imo_no is not None else None
        except Exception:
            logging.warning("Skip row with invalid IMO_no=%r", imo_no)
            continue

        if serial_no is None or channel_no is None or channel_description is None:
            logging.warning("Skip row missing key fields: %r", row)
            continue

        try:
            val_num = float(value) if value is not None and str(value).strip() != "" else None
        except Exception:
            val_num = None

        dg_name, label = split_dg_name_from_label(str(channel_description).strip())

        normalized.append(
            (
                imo_val,
                str(serial_no).strip(),
                dg_name,
                str(channel_no).strip(),
                label,
                str(ts),
                val_num,
                str(unit).strip() if unit is not None else "",
            )
        )
    normalized.sort(key=_sort_key)
    return normalized


def _sort_key(row: tuple) -> tuple:
    # row tuple: (imo, serial, dg_name, addr, label, timestamp, val, unit)
    dg_name = str(row[2]).strip()
    channel_no = str(row[3]).strip()
    if channel_no.isdigit():
        channel_key: tuple[int, int | str] = (0, int(channel_no))
    else:
        channel_key = (1, channel_no)
    return (DG_ORDER.get(dg_name, 99), channel_key)


def replace_into_sqlite(rows: list[tuple], conn: sqlite3.Connection) -> int:
    if not rows:
        return 0
    conn.execute("DELETE FROM live_engine_data;")
    conn.executemany(
        """
        INSERT INTO live_engine_data (imo, serial, dg_name, addr, label, timestamp, val, unit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(imo, serial, dg_name, addr) DO UPDATE SET
            label = excluded.label,
            timestamp = excluded.timestamp,
            val = excluded.val,
            unit = excluded.unit
        WHERE datetime(excluded.timestamp) >= datetime(live_engine_data.timestamp);
        """,
        rows,
    )
    conn.commit()
    cur = conn.execute("SELECT COUNT(1) FROM live_engine_data;")
    return int(cur.fetchone()[0])


def run_once() -> None:
    if not is_data_connection_enabled():
        logging.info("Data connection is disabled by flag file.")
        return

    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    max_ts, mysql_rows = fetch_latest_rows_from_mysql()
    if not mysql_rows:
        logging.info("No rows to import.")
        return

    rows = normalize_sqlite_rows(mysql_rows)
    if not rows:
        logging.warning("No valid rows after normalization at TimeStamp=%s", max_ts)
        return

    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        ensure_sqlite_schema(sqlite_conn)
        imported = replace_into_sqlite(rows, sqlite_conn)
        logging.info(
            "Imported %s MySQL row(s), stored %s deduplicated row(s) into (%s) from MySQL TimeStamp=%s",
            len(rows),
            imported,
            SQLITE_DB_PATH.name,
            max_ts,
        )
    finally:
        sqlite_conn.close()


def run_watch(interval_seconds: int, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            run_once()
        except Exception as exc:
            logging.exception("Unexpected error in run loop: %s", exc)
        stop_event.wait(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect latest rows by max(TimeStamp) from MySQL table H429 and upsert into SQLite."
    )
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help="Polling interval in seconds when running continuously.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

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
            pass

    run_watch(args.interval, stop_event)


if __name__ == "__main__":
    main()
