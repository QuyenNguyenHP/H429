from app.config import (
    ALARM_RULES,
    ANALOG_PROFILE_BY_DG_NAME,
    ANALOG_PROFILE_BY_SERIAL,
    ANALOG_THRESHOLD_PROFILES,
)
from app.schemas import AlarmResponse, DGAlarmStatusResponse, DGAlarmTrigger
from app.services.live_service import get_latest_all


def _severity_for_rule(value: float | None, rule: dict) -> tuple[str | None, str | None]:
    if value is None:
        return None, None

    critical_above = rule.get("critical_above")
    warning_above = rule.get("warning_above")
    critical_below = rule.get("critical_below")
    warning_below = rule.get("warning_below")

    if critical_above is not None and value >= critical_above:
        return "critical", f">= {critical_above}"
    if warning_above is not None and value >= warning_above:
        return "warning", f">= {warning_above}"
    if critical_below is not None and value <= critical_below:
        return "critical", f"<= {critical_below}"
    if warning_below is not None and value <= warning_below:
        return "warning", f"<= {warning_below}"

    return None, None


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


def _is_on_value(value: float | int | str | None) -> bool:
    if isinstance(value, (int, float)):
        return float(value) == 1.0
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "on", "true"}


def _is_ignored_digital_state_label(label: str | None) -> bool:
    normalized = str(label or "").strip().upper()
    if not normalized:
        return True

    ignored_labels = {
        "ENGINE RUN",
        "READY TO START",
        "PRIMING PUMP RUN",
    }
    return normalized in ignored_labels


def _is_digital_alarm_label(label: str | None) -> bool:
    normalized = str(label or "").strip().upper()
    if not normalized:
        return False

    excluded_substrings = (
        "ALARM REPOSE SIGNAL",
    )

    if _is_ignored_digital_state_label(normalized):
        return False
    return not any(token in normalized for token in excluded_substrings)


def get_active_alarms(db) -> list[AlarmResponse]:
    latest = get_latest_all(db)
    alarms: list[AlarmResponse] = []

    for item in latest:
        label = item.label or ""
        for key, rule in ALARM_RULES.items():
            if key.lower() not in label.lower():
                continue
            severity, limit_text = _severity_for_rule(item.value, rule)
            if severity is None:
                continue
            alarms.append(
                AlarmResponse(
                    addr=item.addr,
                    label=item.label,
                    dg_name=item.dg_name,
                    severity=severity,
                    value=item.value,
                    unit=item.unit,
                    timestamp=item.timestamp,
                    message=f"{label} is {severity} ({item.value} {item.unit}), limit {limit_text}",
                )
            )

    alarms.sort(key=lambda a: (a.severity != "critical", a.timestamp), reverse=True)
    return alarms


def get_alarm_status_by_dg(db) -> list[DGAlarmStatusResponse]:
    latest = get_latest_all(db)
    grouped: dict[str, dict] = {}

    for item in latest:
        dg_name = (item.dg_name or "").strip()
        if not dg_name:
            continue
        state = grouped.setdefault(
            dg_name,
            {
                "latest_timestamp": None,
                "analog_triggers": [],
                "digital_triggers": [],
            },
        )
        if state["latest_timestamp"] is None or item.timestamp > state["latest_timestamp"]:
            state["latest_timestamp"] = item.timestamp

        unit = (item.unit or "").strip().lower()
        if unit == "on/off":
            if _is_ignored_digital_state_label(item.label):
                continue
            if _is_on_value(item.value) and _is_digital_alarm_label(item.label):
                state["digital_triggers"].append(
                    DGAlarmTrigger(
                        source="digital",
                        addr=item.addr,
                        label=item.label,
                        value=item.value,
                        unit=item.unit,
                        severity="critical",
                        timestamp=item.timestamp,
                    )
                )
            continue

        profile_key = _pick_profile_key(item.serial, item.dg_name)
        profile = ANALOG_THRESHOLD_PROFILES.get(profile_key, ANALOG_THRESHOLD_PROFILES["default"])
        rule = profile.get((item.label or "").strip())
        if _classify_status(item.value, rule) != "Critical":
            continue

        state["analog_triggers"].append(
            DGAlarmTrigger(
                source="analog",
                addr=item.addr,
                label=item.label,
                value=item.value,
                unit=item.unit,
                severity="critical",
                timestamp=item.timestamp,
            )
        )

    result: list[DGAlarmStatusResponse] = []
    for dg_name in sorted(grouped):
        state = grouped[dg_name]
        analog_triggers = state["analog_triggers"]
        digital_triggers = state["digital_triggers"]
        all_triggers = sorted(
            [*analog_triggers, *digital_triggers],
            key=lambda trigger: (trigger.severity != "critical", trigger.timestamp),
            reverse=True,
        )
        result.append(
            DGAlarmStatusResponse(
                dg_name=dg_name,
                alarm="ON" if all_triggers else "OFF",
                analog_critical_count=len(analog_triggers),
                digital_alarm_count=len(digital_triggers),
                timestamp=state["latest_timestamp"],
                triggers=all_triggers,
            )
        )

    return result
