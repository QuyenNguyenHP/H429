from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import (
    ANALOG_PROFILE_BY_DG_NAME,
    ANALOG_PROFILE_BY_SERIAL,
    ANALOG_THRESHOLD_PROFILES,
)
from app.db import get_db
from app.models import LiveEngineData
from app.schemas import LiveValueResponse
from app.services.live_service import get_latest_all, get_latest_by_addr, get_latest_by_group

router = APIRouter(prefix="/api/live", tags=["live"])


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


def _pick_profile_key(serial: str | None, dg_name: str | None) -> str:
    if serial and serial in ANALOG_PROFILE_BY_SERIAL:
        return ANALOG_PROFILE_BY_SERIAL[serial]
    if dg_name and dg_name in ANALOG_PROFILE_BY_DG_NAME:
        return ANALOG_PROFILE_BY_DG_NAME[dg_name]
    return "default"


def _classify_status(value: float | None, rule: dict | None) -> str:
    if not rule:
        return "N/A"
    if _condition_match(value, rule.get("critical")):
        return "Critical"
    if _condition_match(value, rule.get("warning")):
        return "Warning"
    if _condition_match(value, rule.get("normal")):
        return "Normal"
    return "N/A"


@router.get("/all", response_model=list[LiveValueResponse])
def live_all(db: Session = Depends(get_db)):
    return get_latest_all(db)


@router.get("/timestamp")
def live_latest_timestamp(db: Session = Depends(get_db)):
    latest_ts = db.execute(select(func.max(LiveEngineData.timestamp))).scalar_one_or_none()
    return {"timestamp": latest_ts}


@router.get("/lable_value")
def live_lable_value(db: Session = Depends(get_db)):
    rows = get_latest_all(db)
    return [{"label": r.label, "value": r.value} for r in rows]


@router.get("/analog_lable_value")
def live_analog_lable_value(db: Session = Depends(get_db)):
    rows = get_latest_all(db)
    result = []
    for r in rows:
        if (r.unit or "").strip().lower() == "on/off":
            continue
        profile_key = _pick_profile_key(r.serial, r.dg_name)
        profile = ANALOG_THRESHOLD_PROFILES.get(profile_key, ANALOG_THRESHOLD_PROFILES["default"])
        rule = profile.get((r.label or "").strip())
        result.append(
            {
                "label": r.label,
                "value": r.value,
                "unit": r.unit,
                "dg_name": r.dg_name,
                "status": _classify_status(r.value, rule),
                "profile": profile_key,
                "thresholds": {
                    "normal": (rule or {}).get("normal"),
                    "warning": (rule or {}).get("warning"),
                    "critical": (rule or {}).get("critical"),
                },
            }
        )
    return result


@router.get("/live_digital_value")
def live_digital_value(db: Session = Depends(get_db)):
    rows = get_latest_all(db)
    return [
        {
            "addr": r.addr,
            "label": r.label,
            "value": r.value,
            "unit": r.unit,
            "dg_name": r.dg_name,
            "timestamp": r.timestamp,
        }
        for r in rows
        if (r.unit or "").strip().lower() == "on/off"
    ]


@router.get("/{addr}", response_model=LiveValueResponse)
def live_by_addr(
    addr: str,
    serial: str | None = Query(default=None, description="Filter by DG serial"),
    db: Session = Depends(get_db),
):
    item = get_latest_by_addr(db, addr, serial=serial)
    if item is None:
        raise HTTPException(status_code=404, detail="Address not found")
    return item


@router.get("/group/{group_name}", response_model=list[LiveValueResponse])
def live_by_group(group_name: str, db: Session = Depends(get_db)):
    return get_latest_by_group(db, group_name)
