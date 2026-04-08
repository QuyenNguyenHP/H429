# Engine Touchscreen Backend 🚀

Backend API built with FastAPI + SQLite for the DG engine monitoring system.

## ✨ Key Features

- ⚡ FastAPI-based REST API
- 🗄️ SQLite data source (`data/live_engine_data.db`)
- 🧠 Clear layered structure: `api/`, `services/`, `models/`, `schemas/`
- 🌐 CORS enabled (`CORS_ORIGINS = ["*"]`)
- 📘 Built-in Swagger/OpenAPI docs

## 📁 Folder Structure

```text
backend/
  app/
    main.py
    config.py
    db.py
    models.py
    schemas.py
    api/
      live.py
      trends.py
      alarms.py
      system.py
    services/
      live_service.py
      trend_service.py
      alarm_service.py
      system_service.py
    utils/
      time_utils.py
      formatters.py
  run.py
  requirements.txt
  README.md
```

## 🗄️ Database Configuration

- DB path is configured in `app/config.py`:
  - `DB_PATH = project_root/data/live_engine_data.db`
- Main table used by the API:
  - `live_engine_data`

## 🔌 Current API Endpoints

### Live Data 📡
- `GET /api/live/all`
- `GET /api/live/timestamp`
- `GET /api/live/lable_value`
- `GET /api/live/analog_lable_value`
- `GET /api/live/live_digital_value`
- `GET /api/live/{addr}`
- `GET /api/live/group/{group_name}`

### Trends 📈
- `GET /api/trends/{addr}?hours=1`
- `GET /api/trends/{addr}?from=...&to=...`

### Alarms 🚨
- `GET /api/alarms/active`
- `GET /api/alarms/history`
- `GET /api/alarms/dg_status`

### System 🩺
- `GET /api/system/health`
- `GET /api/system/status`

## ▶️ Run the Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
```

Or run Uvicorn directly:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📘 API Docs

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 🧪 Quick Test

PowerShell:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/live/analog_lable_value" -Method Get | ConvertTo-Json -Depth 5
```

Browser:

- `http://localhost:8000/api/live/analog_lable_value`
- `http://localhost:8000/api/live/live_digital_value`
- `http://localhost:8000/api/alarms/dg_status`

## ⚙️ Implementation Notes

- `analog_lable_value` returns analog points (`unit != "On/Off"`).
- `live_digital_value` is used by both home and DG detail dashboards.
- `alarms/history` is currently a placeholder implementation.
- The endpoint name `lable_value` is intentionally kept for backward compatibility.

## 🛠️ Troubleshooting

1. ❌ API returns `[]`
- Check whether the collector is writing data to `data/live_engine_data.db`.
- Verify that the DB has recent timestamps.

2. 🌐 Frontend cannot fetch API
- Confirm backend is running on the expected host/port (`localhost:8000`).
- Verify frontend API URLs match backend URLs.

3. 📦 Import/module errors
- Run commands from inside the `backend` directory.
- Reinstall dependencies from `requirements.txt`.

4. ⏱️ `/api/live/timestamp` is matched incorrectly
- Ensure static routes are declared before dynamic route `/{addr}` (already handled in current code).

## 📌 Suggested Next Improvements

- 🔐 Add authentication for non-local deployments.
- 🧾 Implement real alarm history persistence.
- 📊 Add richer operational health/metrics endpoints.
