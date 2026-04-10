# Engine Touchscreen Backend 🚀

Backend API built with FastAPI + SQLite for DG/ME monitoring.

## Key Features ✨

- FastAPI REST API ⚡
- SQLite data source (`collector/live_engine_data.db`) 🗄️
- Layered structure (`api/`, `services/`, `models/`, `schemas/`) 🧠
- CORS enabled (`CORS_ORIGINS = ["*"]`) 🌐
- Swagger/OpenAPI docs out of the box 📘

## Folder Structure 📁

```text
backend/
  app/
    main.py
    config.py
    db.py
    models.py
    schemas.py
    api/
      api_dashboard.py
      api_index.py
      alarms.py
      trends.py
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

## Active Routers 🔌

Registered in [`app/main.py`](C:/Users/DAIKAI%20VR/Desktop/H429/backend/app/main.py):

- `/api/dashboard` (main dashboard data)
- `/api/index` (home/index aggregated data)
- `/api/trends`
- `/api/alarms`
- `/api/system`

## API Endpoints (Current) 📡

### Dashboard (`/api/dashboard`) 📊
- `GET /api/dashboard/analog_lable_value`
- `GET /api/dashboard/analog_lable_value_ME`
- `GET /api/dashboard/live_digital_value`
- `GET /api/dashboard/dg_status`

### Index (`/api/index`) 🏠
- `GET /api/index/DG#1` (`/api/index/DG%231` when URL-encoded)
- `GET /api/index/DG#2` (`/api/index/DG%232`)
- `GET /api/index/DG#3` (`/api/index/DG%233`)
- `GET /api/index/ME-PORT`
- `GET /api/index/ME-STBD`

### Trends (`/api/trends`) 📈
- `GET /api/trends/{addr}?hours=...`
- `GET /api/trends/{addr}?from=...&to=...`

### Alarms (`/api/alarms`) 🚨
- `GET /api/alarms/active`
- `GET /api/alarms/history`
- `GET /api/alarms/dg_status`

### System (`/api/system`) 🩺
- `GET /api/system/health`
- `GET /api/system/status`

## Database Notes 🗃️

- DB path is configured in [`app/config.py`](C:/Users/DAIKAI%20VR/Desktop/H429/backend/app/config.py).
- Main table: `live_engine_data`.
- Collector currently imports latest values and upserts by machine key logic.

## Run Backend ▶️

```bash
cd backend
pip install -r requirements.txt
python run.py
```

Or with Uvicorn:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Docs 📘

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Quick Test 🧪

PowerShell:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/dashboard/analog_lable_value" -Method Get | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8000/api/dashboard/analog_lable_value_ME" -Method Get | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8000/api/index/DG%231" -Method Get | ConvertTo-Json -Depth 5
```

Browser:

- `http://localhost:8000/api/dashboard/analog_lable_value`
- `http://localhost:8000/api/dashboard/live_digital_value`
- `http://localhost:8000/api/dashboard/dg_status`
- `http://localhost:8000/api/index/DG%231`

## Troubleshooting 🛠️

1. API returns empty list `[]` ❌
- Check collector import status and recent data in `collector/live_engine_data.db`.
- Verify `timestamp` values are recent.

2. Frontend cannot fetch API 🌐
- Confirm backend is running at `localhost:8000`.
- Verify frontend endpoints match current routes (`/api/dashboard/*`, `/api/index/*`).

3. Import/module errors 📦
- Run commands from `backend/`.
- Reinstall dependencies from `requirements.txt`.

4. Route confusion for `DG#1`/`DG#2`/`DG#3` 🧭
- Use URL-encoded values in HTTP clients: `%23` instead of `#`.
