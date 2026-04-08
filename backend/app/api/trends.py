from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import TrendResponse
from app.services.trend_service import get_trend_by_hours, get_trend_by_range

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.get("/{addr}", response_model=TrendResponse)
def trend_by_addr(
    addr: str,
    hours: int | None = Query(default=1, ge=1, le=168),
    serial: str | None = Query(default=None, description="Filter by DG serial"),
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    if from_ts and to_ts:
        return get_trend_by_range(db, addr, from_ts, to_ts, serial=serial)

    if to_ts and not from_ts:
        from_ts = to_ts - timedelta(hours=hours or 1)
        return get_trend_by_range(db, addr, from_ts, to_ts, serial=serial)

    if from_ts and not to_ts:
        to_ts = datetime.now(timezone.utc)
        return get_trend_by_range(db, addr, from_ts, to_ts, serial=serial)

    return get_trend_by_hours(db, addr, hours=hours or 1, serial=serial)
