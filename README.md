# Engine Touchscreen App ⚙️🖥️

A DG engine monitoring system that includes a backend API, frontend dashboards, and a data collector.

## 🧩 Components Overview

- `backend/` 🚀: FastAPI + SQLite API for live/trend/alarm/system data
- `frontend/` 🌐: UI pages `index.html` (home) and `DGs_dashboard_V2.html` (DG detail)
- `collector/` 📥: scripts for collecting and writing data to the database
- `collector/` 🗄️: stores `live_engine_data.db`

## 📁 Project Structure

```text
engine-touchscreen-app/
  backend/
    app/
      api/
      services/
      utils/
      main.py
      config.py
      db.py
      models.py
      schemas.py
    run.py
    requirements.txt
    README.md
  frontend/
    Asset/
    index.html
    DGs_dashboard_V2.html
    README.md
  collector/
    modbus_collector.py
    data_collector.py
  collector/
    live_engine_data.db
  README.md
```

## 🔌 Main APIs Used by Frontend

- `GET /api/live/analog_lable_value`
- `GET /api/live/live_digital_value`
- `GET /api/alarms/dg_status`

Backend also provides:

- `GET /api/live/all`
- `GET /api/live/timestamp`
- `GET /api/live/lable_value`
- `GET /api/live/{addr}`
- `GET /api/live/group/{group_name}`
- `GET /api/trends/{addr}`
- `GET /api/alarms/active`
- `GET /api/alarms/history`
- `GET /api/system/health`
- `GET /api/system/status`

## ▶️ Quick Start

### 1) Install Python dependencies 🧰

```bash
pip install -r requirements.txt
```

### 2) Run backend 🚀

```bash
cd backend
python run.py
```

Default backend URL: `http://localhost:8000`

### 3) Run frontend 🌐

```bash
cd frontend
python -m http.server 5170
```

Open in browser:

- `http://localhost:5170/index.html`
- `http://localhost:5170/DGs_dashboard_V2.html?dg=1`

### 4) (Optional) Run collector 📥

```bash
cd collector
python data_collector.py
```

## 🚀 Deploy On VPS With systemd / systemctl

Ví dụ dưới đây dùng:

- source code đặt tại `/opt/engine-touchscreen-app`
- user chạy service là `ubuntu`
- backend chạy cổng `8000`
- frontend static server chạy cổng `5170`

Nếu VPS của bạn dùng user hoặc đường dẫn khác, hãy thay lại `User=`, `Group=`, `WorkingDirectory=` và `ExecStart=`.

### 1) Tạo virtualenv và cài dependencies

```bash
cd /opt/engine-touchscreen-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Tạo service cho backend

Tạo file `/etc/systemd/system/engine-backend.service`:

```ini
[Unit]
Description=Engine Touchscreen Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/engine-touchscreen-app/backend
ExecStart=/opt/engine-touchscreen-app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Lưu ý:

- Không dùng `python run.py` trong production vì file này đang bật `reload=True`.
- Database SQLite đang được backend đọc từ `collector/live_engine_data.db`.

### 3) Tạo service cho frontend

Tạo file `/etc/systemd/system/engine-frontend.service`:

```ini
[Unit]
Description=Engine Touchscreen Frontend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/engine-touchscreen-app/frontend
ExecStart=/opt/engine-touchscreen-app/.venv/bin/python -m http.server 5170 --bind 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Sau khi chạy service frontend, có thể truy cập:

- `http://<VPS-IP>:5170/index.html`
- `http://<VPS-IP>:5170/DGs_dashboard_V2.html?dg=DG%231`
- `http://<VPS-IP>:5170/ME_dashboard.html?dg=ME-PORT`

### 4) Reload và enable service

```bash
sudo systemctl daemon-reload
sudo systemctl enable engine-backend
sudo systemctl enable engine-frontend
sudo systemctl start engine-backend
sudo systemctl start engine-frontend
```

### 5) Kiểm tra trạng thái và log

```bash
sudo systemctl status engine-backend
sudo systemctl status engine-frontend
sudo journalctl -u engine-backend -f
sudo journalctl -u engine-frontend -f
```

### 6) Mở port hoặc reverse proxy

- Backend API: `8000`
- Frontend static files: `5170`

Nếu dùng firewall:

```bash
sudo ufw allow 8000/tcp
sudo ufw allow 5170/tcp
```

Frontend hiện tự gọi API theo hostname hiện tại với cổng `8000`, nên khi mở trang từ `http://<VPS-IP>:5170`, frontend sẽ gọi API tới `http://<VPS-IP>:8000`.

## 📘 API Docs

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 🛠️ Important Notes

- `collector/live_engine_data.db` is the shared data source for backend and collector.
- Current frontend favicon: `frontend/Asset/DRUMS_logo_small.png` 🏷️
- `alarms/history` is currently a placeholder implementation.

## 📚 Detailed Docs

- Backend: `backend/README.md`
- Frontend: `frontend/README.md`

## Check_all_status_lable API Summary (Critical)

Backend file: `backend/app/api/Check_all_status_lable.py`

Endpoint:
- `GET /api/check_all_status_lable/all`

Response shape (per machine):
- `dg_name`: `DG#1`, `DG#2`, `DG#3`, `ME-PORT`, `ME-STBD`
- `analog`: list of analog points with `status`
- `digital`: list of digital points with `status`
- `pms`: PMS values for DG#1..DG#3 (`current`, `voltage`, `power_kw`, `power_factor`, `frequency`)

### Analog logic

- Threshold profile is defined in `ANALOG_THRESHOLD_PROFILE`.
- Analog `status` values: `Normal`, `Warning`, `Critical`.
- Labels with no threshold are always `Normal`.
- `FUEL OIL PRESSURE ENGINE INLET` and `LUB OIL PRESSURE` are threshold-checked only when machine is running.

Running condition used for threshold checks:
- DG#1..DG#3: running when digital `ENGINE RUN` is ON/1.
- ME-PORT, ME-STBD: running when analog `M/E REVOLUTION > 0`.

### Digital logic

Special status labels:
- `ENGINE RUN`: `Running` / `Stop`
- `READY TO START`: `Ready` / `Not Ready`
- `PRIMING PUMP RUN`: `Running` / `Stop`
- `No.1..No.6 ALARM REPOSE SIGNAL(...)`: `Repose` / `OFF`

Digital alarm rules with repose interlock:
- For these labels, `Alarm` only when signal value = 1 and related repose signal = 0:
  - `LUB OIL FILTER DIFFERENTIAL PRESSURE HIGH` -> repose No.6
  - `FUEL OIL PRESSURE LOW` -> repose No.2
  - `LUB OIL PRESSURE LOW` -> repose No.2
  - `H.T. WATER PRESSURE LOW` -> repose No.2
  - `L.T. WATER PRESSURE LOW` -> repose No.2
  - `H.T. WATER TEMPERATURE HIGH` -> repose No.1
  - `T/C LUB OIL PRESSURE LOW` -> repose No.2
  - `H.T. WATER TEMPERATURE HIGH (STOP)` -> repose No.1
  - `LUB OIL PRESSURE LOW (STOP)` -> repose No.2
  - `PRIMING LUB OIL PRESSURE LOW` -> repose No.4
- Otherwise (general digital points):
  - value = 1 -> `Alarm`
  - value = 0 -> `Normal`

### Alarm indication in frontend

Current frontend pages use this API as the source of machine state.
Machine Alarm light is ON when:
- any analog point has `status = Critical`, OR
- any digital point has `status = Alarm`.
