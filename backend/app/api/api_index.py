from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LiveEngineData
from app.services.live_service import get_latest_all

router = APIRouter(prefix="/api/index", tags=["index"])

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


def _is_on_value(value) -> bool:
    if isinstance(value, (int, float)):
        return value == 1
    normalized = str(value or "").strip().lower()
    return normalized in {"on", "1", "true"}


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


def _build_status(rows, dg_name: str) -> dict:
    dg_rows = [
        r for r in rows if (r.dg_name or "").strip() == dg_name
    ]
    ready_point = next(
        (r for r in dg_rows if (r.label or "").strip().upper() == "READY TO START"),
        None,
    )
    run_point = next(
        (r for r in dg_rows if (r.label or "").strip().upper() == "ENGINE RUN"),
        None,
    )
    has_alarm = any(
        _is_on_value(r.value)
        for r in dg_rows
        if (r.label or "").strip().upper() not in {"READY TO START", "ENGINE RUN"}
    )
    return {
        "ready": _is_on_value(ready_point.value) if ready_point else False,
        "running": _is_on_value(run_point.value) if run_point else False,
        "alarm": has_alarm,
        "has_data": len(dg_rows) > 0,
    }


def _build_status_me(rows, dg_name: str) -> dict:
    dg_rows = [r for r in rows if (r.dg_name or "").strip() == dg_name]
    dg_digital_rows = [
        r for r in dg_rows if (r.unit or "").strip().lower() == "on/off"
    ]
    dg_analog_rows = [
        r for r in dg_rows if (r.unit or "").strip().lower() != "on/off"
    ]

    run_point = next(
        (r for r in dg_digital_rows if (r.label or "").strip().upper() == "ENGINE RUN"),
        None,
    )
    me_rev_point = next(
        (r for r in dg_analog_rows if (r.label or "").strip().upper() == "M/E REVOLUTION"),
        None,
    )
    me_rev_value = None
    if me_rev_point is not None and me_rev_point.value is not None:
        try:
            me_rev_value = float(me_rev_point.value)
        except (TypeError, ValueError):
            me_rev_value = None

    running = _is_on_value(run_point.value) if run_point else False
    running = running or (me_rev_value is not None and me_rev_value > 0)
    has_alarm = any(_is_on_value(r.value) for r in dg_digital_rows)
    has_data = len(dg_rows) > 0
    ready = has_data and not running and not has_alarm

    return {
        "ready": ready,
        "running": running,
        "alarm": has_alarm,
        "has_data": has_data,
    }


def _get_digital_rows(rows):
    return [
        r
        for r in rows
        if (r.unit or "").strip().lower() == "on/off"
    ]


@router.get("/DG#1")
def dg1_index(db: Session = Depends(get_db)):
    all_rows = get_latest_all(db)
    digital_rows = _get_digital_rows(all_rows)
    return {
        "dg_name": "DG#1",
        "status": _build_status(digital_rows, "DG#1"),
        "pms": {
            field: _fetch_pms_point_db(db, addr)
            for field, addr in PMS_ADDR_MAP["DG#1"].items()
        },
    }


@router.get("/DG#2")
def dg2_index(db: Session = Depends(get_db)):
    all_rows = get_latest_all(db)
    digital_rows = _get_digital_rows(all_rows)
    return {
        "dg_name": "DG#2",
        "status": _build_status(digital_rows, "DG#2"),
        "pms": {
            field: _fetch_pms_point_db(db, addr)
            for field, addr in PMS_ADDR_MAP["DG#2"].items()
        },
    }


@router.get("/DG#3")
def dg3_index(db: Session = Depends(get_db)):
    all_rows = get_latest_all(db)
    digital_rows = _get_digital_rows(all_rows)
    return {
        "dg_name": "DG#3",
        "status": _build_status(digital_rows, "DG#3"),
        "pms": {
            field: _fetch_pms_point_db(db, addr)
            for field, addr in PMS_ADDR_MAP["DG#3"].items()
        },
    }


@router.get("/ME-PORT")
def me_port_index(db: Session = Depends(get_db)):
    all_rows = get_latest_all(db)
    return {
        "dg_name": "ME-PORT",
        "status": _build_status_me(all_rows, "ME-PORT"),
    }


@router.get("/ME-STBD")
def me_stbd_index(db: Session = Depends(get_db)):
    all_rows = get_latest_all(db)
    return {
        "dg_name": "ME-STBD",
        "status": _build_status_me(all_rows, "ME-STBD"),
    }
