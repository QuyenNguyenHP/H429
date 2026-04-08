# Engine Touchscreen App ⚙️🖥️

A DG engine monitoring system that includes a backend API, frontend dashboards, and a data collector.

## 🧩 Components Overview

- `backend/` 🚀: FastAPI + SQLite API for live/trend/alarm/system data
- `frontend/` 🌐: UI pages `index.html` (home) and `DGs_dashboard_V2.html` (DG detail)
- `collector/` 📥: scripts for collecting and writing data to the database
- `data/` 🗄️: stores `live_engine_data.db`

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
  data/
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

## 📘 API Docs

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 🛠️ Important Notes

- `data/live_engine_data.db` is the shared data source for backend and collector.
- Current frontend favicon: `frontend/Asset/DRUMS_logo_small.png` 🏷️
- `alarms/history` is currently a placeholder implementation.

## 📚 Detailed Docs

- Backend: `backend/README.md`
- Frontend: `frontend/README.md`

