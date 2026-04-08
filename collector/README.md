# 🧩 Collector Service (Modbus → SQLite)

This module collects live generator data from Modbus devices and stores it into SQLite for the backend/frontend dashboard.

## ✨ What It Does
- 🔌 Connects to Modbus TCP device(s)
- 📥 Reads analog and digital signals
- 📝 Logs readings to CSV files
- 💾 Upserts latest values into SQLite table `live_engine_data`
- 🔁 Reconnects automatically when connection is lost

## 📁 Main Files
- `data_collector.py` → main collector script
- `modbus_collector.py` → additional collector script (if used)

## 🗄️ Database Path
In `data_collector.py`, the DB path is configured as:

```python
LIVE_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "live_engine_data.db"
```

This means data is written to:
- `engine-touchscreen-app/data/live_engine_data.db`

## 🧱 Table Used
The collector writes into table:
- `live_engine_data`

Typical fields:
- `imo`
- `serial`
- `addr`
- `label`
- `timestamp`
- `val`
- `unit`

## ▶️ How To Run
From project root:

```bash
pip install -r collector/requirements.txt
```

Then run:

```bash
cd collector
python data_collector.py
```

If your environment uses `python3`:

```bash
cd collector
python3 data_collector.py
```

## ⚙️ Config Points (Inside Script)
Edit these values in `data_collector.py` as needed:
- `DG1_IP`
- `DG1_SLAVE_ID`
- `DG1_Name`
- `DG1_SerialNo`
- `CSV_LOG_PREFIX`

## 📤 Output
- CSV files in current working directory (prefix like `H429_...csv`)
- SQLite updates in `data/live_engine_data.db`

### Disable CSV to avoid frontend auto-reload flicker
If you run frontend with a live-reload server, frequent CSV writes can trigger full page reloads.

- Default now: CSV logging is enabled (`ENABLE_CSV_LOG=1`)
- To disable CSV logging:

```bash
ENABLE_CSV_LOG=0 python data_collector.py
```

## 🛠️ Troubleshooting

1. No data in dashboard
- Check collector is running
- Check backend API response:
  - `GET /api/live/analog_lable_value`

2. Modbus connection fails
- Verify IP and slave ID
- Ensure device is reachable from host network

3. SQLite file not updating
- Confirm DB path is correct
- Confirm write permissions for project folders

4. Values look stale
- Collector loop writes periodically (every few seconds)
- Check collector terminal logs for reconnect/errors

## 🔄 Auto-Run on Raspberry Pi with systemd

To automatically start the collector service on boot, create a systemd service.

### Prerequisites
- Ensure Python and required packages are installed:
  ```bash
  sudo apt update
  sudo apt install python3 python3-pip
  pip3 install -r requirements.txt
  ```

### Create Service File
Create a new service file:

```bash
sudo nano /etc/systemd/system/collector.service
```

Add the following content (replace `/path/to/your/project` with the actual path to your `engine-touchscreen-app` directory):

```ini
[Unit]
Description=Engine Data Collector Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/path/to/your/project/engine-touchscreen-app/collector
ExecStart=/usr/bin/python3 data_collector.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable collector.service
sudo systemctl start collector.service
```

### Check Status
```bash
sudo systemctl status collector.service
```

### View Logs
```bash
journalctl -u collector.service -f
```

### Stop/Disable Service (if needed)
```bash
sudo systemctl stop collector.service
sudo systemctl disable collector.service
```

## 📌 Notes
- Collector currently stores latest point per key using upsert logic.
- For long-term history/analytics, consider adding a separate history table in future.
