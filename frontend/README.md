# Engine Touchscreen Frontend 🖥️

Static frontend for the H429 monitoring UI ⚙️

## 1. Folder Structure 📁

```text
frontend/
  Asset/
    DAIKAI_LOGO.jpg
    DRUMS_LOGO.png
    DRUMS_logo_small.png
    Engine.png
    Engine_image.png
    engine_image_mainpage.png
    Engine_Runing.gif
    Engine_Runing_1.gif
  index.html
  DGs_dashboard_V2.html
  ME_dashboard.html
  dashboard_shared.js
  config.js
  index.js
  app.css
  DGs_dashboard.html.bak
  README.md
```

## 2. Active Pages 🌐

- `index.html` 🏠
  - Home page for vessel `H429`
  - Shows DG#1, DG#2, DG#3, ME-STBD, and ME-PORT summary cards
  - Includes `DATA CONNECTION` controls with `Mode 1 / Mode 2`, `Connect`, and status text
  - Loads machine status and PMS values from the backend summary API

- `DGs_dashboard_V2.html` 📊
  - Detail dashboard for `DG#1`, `DG#2`, and `DG#3`
  - DG selector can switch between DG pages and redirect to ME page when needed
  - Uses aggregated status data plus per-machine timestamp API

- `ME_dashboard.html` 🚢
  - Detail dashboard for `ME-PORT` and `ME-STBD`
  - Selector can switch back to DG pages
  - Uses aggregated status data for analog, digital, ready/run, and alarm states

## 3. Shared Files 🧩

- `dashboard_shared.js`
  - Shared DOM helpers
  - DG name normalization
  - Shared fetch timeout helper
  - `resolveApiOrigin()` helper with backend default port `8131`

- `app.css`
  - Shared stylesheet for `index.html`, `DGs_dashboard_V2.html`, and `ME_dashboard.html`
  - Controls layout, card styling, status lights, tables, and engine overlay blocks

- `config.js` and `index.js`
  - Legacy/demo files
  - Still point to backend port `8131`
  - Not part of the main active dashboard flow

- `DGs_dashboard.html.bak`
  - Backup file only 💾
  - Not part of the active UI

## 4. Backend Connection 🔌

Default frontend API origin:

- `http://localhost:8131`

Behavior:

- When served from `http://localhost:5170`, frontend calls backend on port `8131`
- When opened directly with `file://`, `index.html` falls back to `http://localhost:8131`

## 5. API Endpoints Used By Frontend 📡

### `index.html`

- `GET /api/check_all_status_lable/all`
- `GET /api/system/data_connection/status`
- `POST /api/system/data_connection/connect`
- `POST /api/system/data_connection/disconnect`

### `DGs_dashboard_V2.html`

- `GET /api/check_all_status_lable/all`
- `GET /api/timestamp?dg_name=...`

### `ME_dashboard.html`

- `GET /api/check_all_status_lable/all`

## 6. Run Frontend ▶️

Run a static server:

```bash
cd frontend
python -m http.server 5170 --bind 0.0.0.0
```

Then open:

- `http://localhost:5170/index.html`
- `http://localhost:5170/DGs_dashboard_V2.html?dg=DG%231`
- `http://localhost:5170/ME_dashboard.html?dg=ME-PORT`

Backend should be running at:

- `http://localhost:8131`

## 7. Navigation Flow 🔁

- `index.html` -> DG cards open `DGs_dashboard_V2.html`
- `index.html` -> ME cards open `ME_dashboard.html`
- `DGs_dashboard_V2.html` -> selecting `ME-PORT` or `ME-STBD` redirects to `ME_dashboard.html`
- `ME_dashboard.html` -> selecting `DG#1`, `DG#2`, or `DG#3` redirects to `DGs_dashboard_V2.html`
- Clicking the DRUMS logo on detail pages returns to `index.html`

## 8. Notes 📝

- Status lights are now steady and do not blink 💡
- `FAIL CONNECTION !` text on the home page still blinks when data is missing ⚠️
- If CSS or image changes do not appear immediately, use `Ctrl + F5` 🔄
