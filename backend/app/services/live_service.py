from sqlalchemy import case, cast, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import Integer

from app.models import LiveEngineData
from app.schemas import LiveValueResponse


def get_latest_all(db: Session) -> list[LiveValueResponse]:
    # Collector already upserts one latest row per (serial, addr), so fetch all rows directly.
    dg_order = case(
        (LiveEngineData.dg_name == "DG#1", 1),
        (LiveEngineData.dg_name == "DG#2", 2),
        (LiveEngineData.dg_name == "DG#3", 3),
        (LiveEngineData.dg_name == "ME-PORT", 4),
        (LiveEngineData.dg_name == "ME-STBD", 5),
        else_=99,
    )
    stmt = select(LiveEngineData).order_by(
        dg_order,
        LiveEngineData.serial,
        cast(LiveEngineData.addr, Integer),
    )

    rows = db.execute(stmt).scalars().all()
    return [
        LiveValueResponse(
            addr=r.addr,
            serial=r.serial,
            label=r.label,
            dg_name=r.dg_name,
            value=r.val,
            unit=r.unit,
            timestamp=r.timestamp,
        )
        for r in rows
    ]


def get_latest_by_addr(db: Session, addr: str, serial: str | None = None) -> LiveValueResponse | None:
    stmt = select(LiveEngineData).where(LiveEngineData.addr == addr)
    if serial:
        stmt = stmt.where(LiveEngineData.serial == serial)
    stmt = stmt.order_by(LiveEngineData.timestamp.desc()).limit(1)
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        return None
    return LiveValueResponse(
        addr=row.addr,
        serial=row.serial,
        label=row.label,
        dg_name=row.dg_name,
        value=row.val,
        unit=row.unit,
        timestamp=row.timestamp,
    )


def get_latest_by_group(db: Session, group_name: str) -> list[LiveValueResponse]:
    all_rows = get_latest_all(db)
    keyword = group_name.strip().lower()
    return [r for r in all_rows if (r.label or "").lower().find(keyword) >= 0]
