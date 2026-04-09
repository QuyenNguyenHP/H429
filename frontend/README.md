# Engine Touchscreen Frontend 🖥️

Static frontend for DG and ME monitoring dashboards ⚙️

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
  DGs_dashboard.html.bak
  config.js
  index.js
  app.css
  README.md
```

## 2. Active Pages 🌐

- `index.html`
  - Home page 🏠
  - DG#1, DG#2, DG#3 cards open `DGs_dashboard_V2.html`.
  - ME-STBD and ME-PORT cards open `ME_dashboard.html`.
  - Uses aggregated status/PMS API from `/api/index/*` 🔗

- `DGs_dashboard_V2.html`
  - DG detail page for DG#1, DG#2, DG#3 📊
  - Includes selector with DG and ME options.
  - If user selects ME-* from this page, it redirects to `ME_dashboard.html` 🔀

- `ME_dashboard.html`
  - ME detail page for ME-PORT and ME-STBD 🚢
  - Includes selector with DG and ME options.
  - If user selects DG#1/2/3 from this page, it redirects to `DGs_dashboard_V2.html` 🔀

## 3. Shared Script 🧩

- `dashboard_shared.js` contains shared helpers used by both dashboards:
  - DOM helper (`getById`) 🏷️
  - DG name normalization
  - Filter rows by selected machine
  - ON/OFF normalization
  - Layout helper (`applyLayoutToElement`) 📐
  - Fetch timeout helper (`fetchWithTimeout`) ⏱️

This file is loaded by:
- `DGs_dashboard_V2.html`
- `ME_dashboard.html`

## 4. API Endpoints Used by Frontend 🔌

Base URL in frontend:
- `http://localhost:8000`

### `index.html`
- `GET /api/index/DG%231`
- `GET /api/index/DG%232`
- `GET /api/index/DG%233`
- `GET /api/index/ME-PORT`
- `GET /api/index/ME-STBD`

### `DGs_dashboard_V2.html`
- `GET /api/dashboard/analog_lable_value` (DG mode)
- `GET /api/dashboard/analog_lable_value_ME` (fallback when target is ME)
- `GET /api/dashboard/live_digital_value`
- `GET /api/dashboard/dg_status`

### `ME_dashboard.html`
- `GET /api/dashboard/analog_lable_value_ME`
- `GET /api/dashboard/live_digital_value`
- `GET /api/dashboard/dg_status`

## 5. Run Frontend ▶️

Open HTML files directly, or run a static server:

```bash
cd frontend
python -m http.server 5170
```

Then open:

- `http://localhost:5170/index.html`
- `http://localhost:5170/DGs_dashboard_V2.html?dg=DG%231`
- `http://localhost:5170/ME_dashboard.html?dg=ME-PORT`

## 6. Notes 📝

- `DGs_dashboard.html.bak` is a backup file, not an active page 💾
- `config.js`, `index.js`, `app.css` are legacy files and are not currently imported by active pages 🧹
- If icon/logo/CSS changes are not visible immediately, hard refresh with `Ctrl + F5` 🔄
