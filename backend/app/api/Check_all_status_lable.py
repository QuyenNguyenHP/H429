from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LiveEngineData
from app.services.live_service import get_latest_all

router = APIRouter(prefix="/api/check_all_status_lable", tags=["check_all_status_lable"])

TARGET_MACHINES = {"DG#1", "DG#2", "DG#3", "ME-PORT", "ME-STBD"}
ME_MACHINES = {"ME-PORT", "ME-STBD"}

PMS_ADDR_MAP = {
    "DG#1": {
        "current": "40011",
        "voltage": "40019",
        "power_kw": "40029",
        "power_factor": "40031",
        "frequency": "40033",
    },
    "DG#2": {
        "current": "40045",
        "voltage": "40053",
        "power_kw": "40063",
        "power_factor": "40065",
        "frequency": "40067",
    },
    "DG#3": {
        "current": "40079",
        "voltage": "40087",
        "power_kw": "40097",
        "power_factor": "40099",
        "frequency": "40101",
    },
}

ANALOG_THRESHOLD_PROFILE = {
    "LUB OIL TEMPERATURE ENGINE INLET": {
        "normal": {"lt": 60},
        "warning": {"gte": 60, "lt": 65},
        "critical": {"gte": 65},
    },
    "H.T. WATER TEMPERATURE ENGINE OUTLET": {
        "normal": {"lt": 80},
        "warning": {"gte": 80, "lt": 90},
        "critical": {"gte": 90},
    },
    "NO.1CYL. EXHAUST GAS TEMPERATURE": {
        "normal": {"lt": 400},
        "warning": {"gte": 400, "lt": 480},
        "critical": {"gte": 480},
    },
    "NO.2CYL. EXHAUST GAS TEMPERATURE": {
        "normal": {"lt": 400},
        "warning": {"gte": 400, "lt": 480},
        "critical": {"gte": 480},
    },
    "EXHAUST GAS TEMPERATURE T/C INLET 1": {
        "normal": {"lt": 480},
        "warning": {"gte": 480, "lt": 580},
        "critical": {"gte": 580},
    },
    "EXHAUST GAS TEMPERATURE T/C INLET 2": {
        "normal": {"lt": 480},
        "warning": {"gte": 480, "lt": 580},
        "critical": {"gte": 580},
    },
    "H.T. WATER PRESSURE ENGINE INLET": {},
    "L.T. WATER PRESSURE ENGINE INLET": {},
    "STARTING AIR PRESSURE": {
        "normal": {"gt": 2.0},
        "warning": {"gt": 1.5, "lte": 2.0},
        "critical": {"lte": 1.5},
    },
    "FUEL OIL PRESSURE ENGINE INLET": {
        "normal": {"gt": 0.35},
        "warning": {"gt": 0.3, "lte": 0.35},
        "critical": {"lte": 0.3},
    },
    "LUB OIL PRESSURE": {
        "normal": {"gt": 0.35},
        "warning": {"gt": 0.3, "lte": 0.35},
        "critical": {"lte": 0.3},
    },
    "ENGINE SPEED": {
        "normal": {"lt": 900},
        "warning": {"gte": 900, "lt": 1020},
        "critical": {"gte": 1020},
    },
    "LOAD": {},
    "RUNNING HOUR": {},
}

RUN_REQUIRED_LABELS = {"FUEL OIL PRESSURE ENGINE INLET", "LUB OIL PRESSURE"}

DIGITAL_SPECIAL_VALUE_STATUS = {
    "ENGINE RUN": ("Stop", "Running"),
    "READY TO START": ("Not Ready", "Ready"),
    "PRIMING PUMP RUN": ("Stop", "Running"),
    "NO.1 ALARM REPOSE SIGNAL(#14)": ("OFF", "Repose"),
    "NO.2 ALARM REPOSE SIGNAL(#14T)": ("OFF", "Repose"),
    "NO.3 ALARM REPOSE SIGNAL(EXH. GAS)": ("OFF", "Repose"),
    "NO.4 ALARM REPOSE SIGNAL(PRIMING)": ("OFF", "Repose"),
    "NO.5 ALARM REPOSE SIGNAL(STARTING)": ("OFF", "Repose"),
    "NO.6 ALARM REPOSE SIGNAL(FILTER DIFF. PRESS.)": ("OFF", "Repose"),
}

DIGITAL_ALARM_WITH_REPOSE = {
    "LUB OIL FILTER DIFFERENTIAL PRESSURE HIGH": "NO.6 ALARM REPOSE SIGNAL(FILTER DIFF. PRESS.)",
    "FUEL OIL PRESSURE LOW": "NO.2 ALARM REPOSE SIGNAL(#14T)",
    "LUB OIL PRESSURE LOW": "NO.2 ALARM REPOSE SIGNAL(#14T)",
    "H.T. WATER PRESSURE LOW": "NO.2 ALARM REPOSE SIGNAL(#14T)",
    "L.T. WATER PRESSURE LOW": "NO.2 ALARM REPOSE SIGNAL(#14T)",
    "H.T. WATER TEMPERATURE HIGH": "NO.1 ALARM REPOSE SIGNAL(#14)",
    "T/C LUB OIL PRESSURE LOW": "NO.2 ALARM REPOSE SIGNAL(#14T)",
    "H.T. WATER TEMPERATURE HIGH (STOP)": "NO.1 ALARM REPOSE SIGNAL(#14)",
    "LUB OIL PRESSURE LOW (STOP)": "NO.2 ALARM REPOSE SIGNAL(#14T)",
    "PRIMING LUB OIL PRESSURE LOW": "NO.4 ALARM REPOSE SIGNAL(PRIMING)",
}


def _norm_label(label: str | None) -> str:
    return str(label or "").strip().upper()


def _normalize_dg_name(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip().upper().replace(" ", "").replace("_", "-")
    if raw in {"DG1", "DG#1", "DG-1"}:
        return "DG#1"
    if raw in {"DG2", "DG#2", "DG-2"}:
        return "DG#2"
    if raw in {"DG3", "DG#3", "DG-3"}:
        return "DG#3"
    if raw == "ME-PORT":
        return "ME-PORT"
    if raw == "ME-STBD":
        return "ME-STBD"
    return None


def _to_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_pms_point_db(db: Session, addr: str) -> dict | None:
    stmt = (
        select(LiveEngineData)
        .where(LiveEngineData.dg_name == "PMS", LiveEngineData.addr == addr)
        .order_by(LiveEngineData.timestamp.desc())
        .limit(1)
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        return None
    return {
        "addr": row.addr,
        "value": row.val,
        "unit": row.unit,
        "timestamp": row.timestamp,
    }


def _is_running_for_machine(dg_name: str, digital_by_label: dict[str, object], analog_rows: list) -> bool:
    if dg_name in ME_MACHINES:
        me_rev_point = next((r for r in analog_rows if _norm_label(r.label) == "M/E REVOLUTION"), None)
        me_rev_value = _to_float(me_rev_point.value) if me_rev_point else None
        return (me_rev_value or 0) > 0
    engine_run_row = digital_by_label.get("ENGINE RUN")
    return _is_on(engine_run_row.value) if engine_run_row else False


def _is_on(value) -> bool:
    if isinstance(value, (int, float)):
        return float(value) == 1.0
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "on", "true", "yes"}


def _condition_match(value: float | None, cond: dict | None) -> bool:
    if value is None or not cond:
        return False
    if "gt" in cond and not (value > cond["gt"]):
        return False
    if "gte" in cond and not (value >= cond["gte"]):
        return False
    if "lt" in cond and not (value < cond["lt"]):
        return False
    if "lte" in cond and not (value <= cond["lte"]):
        return False
    return True


def _analog_status(label: str, value: float | None, is_running: bool) -> str:
    rule = ANALOG_THRESHOLD_PROFILE.get(label)
    if rule is None:
        return "Normal"
    if not rule:
        return "Normal"
    if label in RUN_REQUIRED_LABELS and not is_running:
        return "Normal"
    if _condition_match(value, rule.get("critical")):
        return "Critical"
    if _condition_match(value, rule.get("warning")):
        return "Warning"
    if _condition_match(value, rule.get("normal")):
        return "Normal"
    return "Normal"


def _digital_status(
    label: str,
    value,
    repose_by_label: dict[str, bool],
) -> str:
    if label in DIGITAL_SPECIAL_VALUE_STATUS:
        off_text, on_text = DIGITAL_SPECIAL_VALUE_STATUS[label]
        return on_text if _is_on(value) else off_text

    repose_label = DIGITAL_ALARM_WITH_REPOSE.get(label)
    if repose_label:
        repose_on = repose_by_label.get(repose_label, False)
        return "Alarm" if _is_on(value) and not repose_on else "Normal"
    return "Alarm" if _is_on(value) else "Normal"


@router.get("/all")
def check_all_status_lable(db: Session = Depends(get_db)):
    rows = get_latest_all(db)

    machine_rows: dict[str, list] = {name: [] for name in TARGET_MACHINES}
    for row in rows:
        dg_name = _normalize_dg_name(row.dg_name)
        if dg_name not in TARGET_MACHINES:
            continue
        machine_rows[dg_name].append(row)

    output = []
    for dg_name in sorted(machine_rows.keys()):
        dg_rows = machine_rows[dg_name]

        digital_rows = [r for r in dg_rows if (r.unit or "").strip().lower() == "on/off"]
        analog_rows = [r for r in dg_rows if (r.unit or "").strip().lower() != "on/off"]

        digital_by_label = {_norm_label(r.label): r for r in digital_rows}
        repose_by_label = {
            key: _is_on(digital_by_label.get(key).value) if digital_by_label.get(key) else False
            for key in {
                "NO.1 ALARM REPOSE SIGNAL(#14)",
                "NO.2 ALARM REPOSE SIGNAL(#14T)",
                "NO.3 ALARM REPOSE SIGNAL(EXH. GAS)",
                "NO.4 ALARM REPOSE SIGNAL(PRIMING)",
                "NO.5 ALARM REPOSE SIGNAL(STARTING)",
                "NO.6 ALARM REPOSE SIGNAL(FILTER DIFF. PRESS.)",
            }
        }
        is_running = _is_running_for_machine(dg_name, digital_by_label, analog_rows)

        analog_result = []
        for r in analog_rows:
            label = _norm_label(r.label)
            analog_result.append(
                {
                    "addr": r.addr,
                    "label": r.label,
                    "value": r.value,
                    "unit": r.unit,
                    "timestamp": r.timestamp,
                    "status": _analog_status(label, _to_float(r.value), is_running),
                }
            )

        digital_result = []
        for r in digital_rows:
            label = _norm_label(r.label)
            digital_result.append(
                {
                    "addr": r.addr,
                    "label": r.label,
                    "value": r.value,
                    "unit": r.unit,
                    "timestamp": r.timestamp,
                    "status": _digital_status(label, r.value, repose_by_label),
                }
            )

        output.append(
            {
                "dg_name": dg_name,
                "analog": analog_result,
                "digital": digital_result,
                "pms": {
                    field: _fetch_pms_point_db(db, addr)
                    for field, addr in PMS_ADDR_MAP.get(dg_name, {}).items()
                },
            }
        )

    return output
