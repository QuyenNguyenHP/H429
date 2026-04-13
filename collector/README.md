# Collector Service 📥

Collector module for H429 data import and SQLite sync ⚙️

## 1. What This Folder Contains 📁

```text
collector/
  csv_received/
  csv_archived/
  Public_key_to_decrypt_asc_file/
  live_engine_data.db
  mode1_import_data_from_drums.py
  mode2_data_collector_from_database.py
  requirements.txt
  README.md
```

## 2. Main Purpose 🎯

This folder is responsible for keeping `live_engine_data.db` up to date for the backend/frontend.

It currently supports 2 data modes:

- `Mode 1` 📦
  - Reads the newest file from `csv_received/`
  - Supports both `.csv` and `.zip`
  - Imports data into SQLite
  - Archives the processed source file into `csv_archived/`

- `Mode 2` 🗄️
  - Connects to a MySQL source
  - Pulls the latest rows by `MAX(TimeStamp)`
  - Normalizes them
  - Replaces data in local SQLite

## 3. Active Scripts 🚀

- `mode1_import_data_from_drums.py`
  - Main collector for uploaded DRUMS files
  - Watches `csv_received/`
  - Handles merged CSV and zipped CSV input
  - Writes to `live_engine_data.db`
  - Uses backend flag file `.data_connection_enabled` to decide whether import should run

- `mode2_data_collector_from_database.py`
  - Collector for MySQL database mode
  - Pulls latest source rows from remote MySQL
  - Rebuilds the SQLite live table from normalized rows
  - Also respects backend `.data_connection_enabled`

## 4. Database Path 🗄️

SQLite is stored at:

- `collector/live_engine_data.db`

Used table:

- `live_engine_data`

Main columns:

- `imo`
- `serial`
- `dg_name`
- `addr`
- `label`
- `timestamp`
- `val`
- `unit`

## 5. Mode 1 Flow 🔄

Source folders:

- `csv_received/` → incoming files waiting to import
- `csv_archived/` → processed files after successful import

Behavior:

- Selects the newest file in `csv_received/`
- Accepts `.csv` or `.zip`
- If input is `.zip`, extracts the newest CSV from inside the archive
- Parses DRUMS merged rows such as:
  - `imo,serial,addr,label,timestamp,val,unit`
- Splits machine name from label when needed:
  - `DG#1 ...`
  - `ME_PORT ...`
  - `ME_STBD ...`
  - `PMS ...`
- Imports into SQLite and then archives the original source file
- Cleans temporary extracted files after import

Important files:

- `csv_received/H429_merged_*.csv`
- `csv_received/H429_merged_*.zip`

## 6. Mode 2 Flow 🌐

Mode 2 reads directly from MySQL using environment variables.

Default variables in script:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`
- `MYSQL_TABLE`

Behavior:

- Connects to MySQL
- Reads rows at latest `TimeStamp`
- Normalizes `dg_name` and `label`
- Replaces all rows in `live_engine_data.db`

## 7. Connection Control 🔌

Both mode scripts check the backend flag file:

- `backend/.data_connection_enabled`

Current behavior:

- `mode1_import_data_from_drums.py`
  - Stops importing when the flag is missing or disabled

- `mode2_data_collector_from_database.py`
  - Runs by default if the flag file is missing
  - Stops only when the flag exists and is set to disabled

This is used by the frontend/backend `DATA CONNECTION` control on the home page 🧭

## 8. How To Run ▶️

Install dependencies:

```bash
pip install -r collector/requirements.txt
```

Run Mode 1 once:

```bash
cd collector
python mode1_import_data_from_drums.py --once
```

Run Mode 1 continuously:

```bash
cd collector
python mode1_import_data_from_drums.py
```

Run Mode 2 once:

```bash
cd collector
python mode2_data_collector_from_database.py --once
```

Run Mode 2 continuously:

```bash
cd collector
python mode2_data_collector_from_database.py
```

## 9. Environment Variables ⚙️

### Mode 1

- `CSV_IMPORT_INTERVAL`
  - Polling interval in seconds
  - Default: `5`

### Mode 2

- `DB_IMPORT_INTERVAL`
  - Polling interval in seconds
  - Default: `210`

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`
- `MYSQL_TABLE`

## 10. Output Summary 📤

- Imported live data goes to:
  - `collector/live_engine_data.db`

- Incoming source files come from:
  - `collector/csv_received/`

- Processed source files move to:
  - `collector/csv_archived/`

## 11. Troubleshooting 🛠️

1. No data in frontend ❌
- Check backend is reading from `collector/live_engine_data.db`
- Confirm the selected collector mode is running
- Check `backend/.data_connection_enabled`

2. Files stay in `csv_received/` 📄
- Check importer logs for parse/import errors
- Verify the file is a valid DRUMS merged CSV or ZIP containing CSV

3. ZIP file does not import 📦
- Make sure the ZIP actually contains at least one `.csv`
- Script will select the newest CSV member inside the ZIP

4. SQLite is not updated 🗃️
- Confirm write permission on `collector/`
- Confirm no other process is locking `live_engine_data.db`

5. Mode 2 cannot read MySQL 🌐
- Verify host, port, user, password, database, and table
- Ensure a MySQL driver is installed:
  - `pymysql`
  - or `mysql-connector-python`

## 12. Notes 📝

- `live_engine_data.db` is the live data source used by backend APIs
- `mode1_import_data_from_drums.py` is the current replacement for the older CSV import flow
- `Public_key_to_decrypt_asc_file/` exists in this folder, but decryption flow is not handled in the current README
