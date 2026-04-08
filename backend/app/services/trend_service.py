from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LiveEngineData
from app.schemas import TrendPoint, TrendResponse


def _series(
    db: Session, addr: str, start_dt: datetime, end_dt: datetime, serial: str | None = None
) -> TrendResponse:
    stmt = select(LiveEngineData).where(
        LiveEngineData.addr == addr,
        LiveEngineData.timestamp >= start_dt,
        LiveEngineData.timestamp <= end_dt,
    )
    if serial:
        stmt = stmt.where(LiveEngineData.serial == serial)
    stmt = stmt.order_by(LiveEngineData.timestamp.asc())
    rows = db.execute(stmt).scalars().all()
    return TrendResponse(
        addr=addr,
        points=[TrendPoint(timestamp=r.timestamp, value=r.val) for r in rows],
    )


def get_trend_by_hours(
    db: Session, addr: str, hours: int = 1, serial: str | None = None
) -> TrendResponse:
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(hours=hours)
    return _series(db, addr, start_dt, end_dt, serial=serial)


def get_trend_by_range(
    db: Session, addr: str, start_dt: datetime, end_dt: datetime, serial: str | None = None
) -> TrendResponse:
    return _series(db, addr, start_dt, end_dt, serial=serial)
