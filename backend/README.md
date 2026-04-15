# Engine Touchscreen Backend ðŸš€

FastAPI backend for H429 DG/ME monitoring âš™ï¸

## 1. What This Backend Does ðŸ§ 

- Serves live monitoring APIs for DG and ME pages ðŸ“¡
- Reads live data from SQLite ðŸ—„ï¸
- Aggregates analog, digital, alarm, PMS, and timestamp data ðŸ“Š
- Exposes system status and data connection control endpoints ðŸ”Œ
- Supports Swagger/OpenAPI docs out of the box ðŸ“˜

## 2. Folder Structure ðŸ“

```text
backend/
  app/
    api/
      api_dashboard.py
      api_index.py
      Check_all_status_lable.py
      system.py
      timestamp.py
      trends.py
    services/
      alarm_service.py
      live_service.py
      system_service.py
      trend_service.py
    utils/
      formatters.py
      time_utils.py
    config.py
    db.py
    main.py
    models.py
    schemas.py
  .data_connection_enabled
  .data_connection_state.json
  run.py
  requirements.txt
  README.md
```

## 3. Runtime Basics â–¶ï¸

- Backend default port: `8131`
- Start script: `backend/run.py`
- App entry: `app.main:app`

Run locally:

```bash
cd backend
pip install -r requirements.txt
python run.py
```

Or run with Uvicorn:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8131 --reload
```

## 4. SQLite Data Source ðŸ—„ï¸

Backend reads from:

- `collector/live_engine_data.db`

Configured in:

- [config.py](/c:/Users/DAIKAI%20VR/Desktop/H429/backend/app/config.py:7)

Main table:

- `live_engine_data`

Important columns:

- `imo`
- `serial`
- `dg_name`
- `addr`
- `label`
- `timestamp`
- `val`
- `unit`

## 5. Active Routers ðŸŒ

Registered in [main.py](/c:/Users/DAIKAI%20VR/Desktop/H429/backend/app/main.py:28):

- `/api/dashboard` ðŸ“Š
- `/api/index` ðŸ 
- `/api/check_all_status_lable` âœ…
- `/api/system` ðŸ©º
- `/api/timestamp` ðŸ•’
- `/api/trends` ðŸ“ˆ

## 6. Main API Groups ðŸ“¡

### Dashboard APIs ðŸ“Š

From [api_dashboard.py](/c:/Users/DAIKAI%20VR/Desktop/H429/backend/app/api/api_dashboard.py:14):

- `GET /api/dashboard/analog_lable_value`
- `GET /api/dashboard/analog_lable_value_ME`
- `GET /api/dashboard/live_digital_value`
- `GET /api/dashboard/dg_status`

### Index APIs ðŸ 

From [api_index.py](/c:/Users/DAIKAI%20VR/Desktop/H429/backend/app/api/api_index.py:9):

- `GET /api/index/DG#1`
- `GET /api/index/DG#2`
- `GET /api/index/DG#3`
- `GET /api/index/ME-PORT`
- `GET /api/index/ME-STBD`

Use URL-encoded `#` when calling from browser/client:

- `/api/index/DG%231`
- `/api/index/DG%232`
- `/api/index/DG%233`

### Aggregated Status API âœ…

From [Check_all_status_lable.py](/c:/Users/DAIKAI%20VR/Desktop/H429/backend/app/api/Check_all_status_lable.py:9):

- `GET /api/check_all_status_lable/all`

Used by frontend home page and detail pages.

Returns grouped machine payloads for:

- `DG#1`
- `DG#2`
- `DG#3`
- `ME-PORT`
- `ME-STBD`

Includes:

- `analog`
- `digital`
- `pms`
- machine-level grouped status data

### Timestamp API ðŸ•’

From [timestamp.py](/c:/Users/DAIKAI%20VR/Desktop/H429/backend/app/api/timestamp.py:8):

- `GET /api/timestamp`
- Example: `GET /api/timestamp?dg_name=DG%231`

### System APIs ðŸ©º

From [system.py](/c:/Users/DAIKAI%20VR/Desktop/H429/backend/app/api/system.py:15):

- `GET /api/system/health`
- `GET /api/system/status`
- `GET /api/system/data_connection/status`
- `POST /api/system/data_connection/connect`
- `POST /api/system/data_connection/disconnect`

These endpoints are used by the `DATA CONNECTION` controls in `frontend/index.html`.

### Trend API ðŸ“ˆ

From [trends.py](/c:/Users/DAIKAI%20VR/Desktop/H429/backend/app/api/trends.py:10):

- `GET /api/trends/{addr}?hours=...`
- `GET /api/trends/{addr}?from=...&to=...`

## 7. Data Connection Control ðŸ”Œ

Backend stores data connection state using:

- `backend/.data_connection_enabled`
- `backend/.data_connection_state.json`

Current behavior:

- Checks whether backend port `8131` is open
- Starts collector script depending on selected mode
- Tracks collector mode and process state
- Lets frontend connect/disconnect through API

Configured collector script paths in [system.py](/c:/Users/DAIKAI%20VR/Desktop/H429/backend/app/api/system.py:19):

- `mode2_import_data_from_drums.py`
- `mode1_data_collector_from_database.py`

## 8. Docs And Quick Test ðŸ§ª

Swagger:

- `http://localhost:8131/docs`
- `http://localhost:8131/openapi.json`

PowerShell quick test:

```powershell
Invoke-RestMethod -Uri "http://localhost:8131/api/check_all_status_lable/all" -Method Get | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri "http://localhost:8131/api/index/DG%231" -Method Get | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8131/api/system/health" -Method Get | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8131/api/timestamp?dg_name=DG%231" -Method Get | ConvertTo-Json -Depth 5
```

Browser quick check:

- `http://localhost:8131/api/check_all_status_lable/all`
- `http://localhost:8131/api/index/DG%231`
- `http://localhost:8131/api/system/health`
- `http://localhost:8131/docs`

## 9. Frontend Dependencies ðŸ”—

Frontend currently depends on these backend groups:

- `index.html`
  - `/api/check_all_status_lable/all`
  - `/api/system/data_connection/status`
  - `/api/system/data_connection/connect`
  - `/api/system/data_connection/disconnect`

- `DGs_dashboard_V2.html`
  - `/api/check_all_status_lable/all`
  - `/api/timestamp`

- `ME_dashboard.html`
  - `/api/check_all_status_lable/all`

## 10. Troubleshooting ðŸ› ï¸

1. Frontend cannot fetch API ðŸŒ
- Confirm backend is running at `http://localhost:8131`
- Confirm frontend also points to port `8131`

2. API returns empty or stale data âŒ
- Check `collector/live_engine_data.db`
- Verify collector mode is running
- Verify `timestamp` values are updating

3. Data connection button does not work ðŸ”Œ
- Check backend `.data_connection_enabled`
- Check `.data_connection_state.json`
- Check collector script paths in `system.py`

4. DG index route looks wrong because of `#` ðŸ§­
- Use URL encoding:
  - `DG#1` -> `DG%231`
  - `DG#2` -> `DG%232`
  - `DG#3` -> `DG%233`

5. Import or DB errors ðŸ“¦
- Run commands from `backend/`
- Confirm SQLite file exists at `collector/live_engine_data.db`
- Reinstall backend dependencies if needed

## 11. Notes ðŸ“

- CORS is enabled with `CORS_ORIGINS = ["*"]`
- Root endpoint `/` returns simple app metadata
- Backend creates tables on startup through FastAPI lifespan

