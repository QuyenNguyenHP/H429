from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LiveValueResponse(BaseModel):
    addr: str
    serial: str | None = None
    label: str | None = None
    dg_name: str | None = None
    value: float | None = None
    unit: str | None = None
    timestamp: datetime


class TrendPoint(BaseModel):
    timestamp: datetime
    value: float | None = None


class TrendResponse(BaseModel):
    addr: str
    points: list[TrendPoint]


class AlarmResponse(BaseModel):
    addr: str
    label: str | None = None
    dg_name: str | None = None
    severity: str
    value: float | None = None
    unit: str | None = None
    timestamp: datetime
    message: str


class DGAlarmTrigger(BaseModel):
    source: str
    addr: str
    label: str | None = None
    value: float | None = None
    unit: str | None = None
    severity: str | None = None
    timestamp: datetime


class DGAlarmStatusResponse(BaseModel):
    dg_name: str
    alarm: str
    analog_critical_count: int
    digital_alarm_count: int
    timestamp: datetime | None = None
    triggers: list[DGAlarmTrigger]


class SystemHealthResponse(BaseModel):
    status: str
    db_path: str
    db_exists: bool
    last_update_time: datetime | None = None


class SystemStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    app_name: str
    version: str
    disk_total_gb: float | None = None
    disk_used_gb: float | None = None
    disk_free_gb: float | None = None
    cpu_temp_c: float | None = None
    utc_time: datetime
    last_update_time: datetime | None = None
