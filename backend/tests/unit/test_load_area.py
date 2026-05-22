from datetime import datetime, timezone

import pytest

from app.load_control.domain.entities import (
    Charger,
    ChargingSession,
    LoadRule,
    LoadRuleType,
    SessionStatus,
)
from app.load_control.domain.load_area import LoadArea
from app.load_control.domain.value_objects import AreaCode, LoadStatus, LoadThresholds, PowerLevel

pytestmark = pytest.mark.unit


def _session(index: int, kw: float, charger: str) -> ChargingSession:
    return ChargingSession(
        session_id=f"s{index}",
        area_code="YN",
        charger_id=charger,
        requested_power=PowerLevel(kw),
        current_power=PowerLevel(kw),
        status=SessionStatus.ACTIVE,
        started_at=datetime.now(timezone.utc),
    )


def make_area(session_kw: list[float], reduction: float = 0.10, max_kw: float = 240.0) -> LoadArea:
    chargers = [Charger(f"YN-{i:02d}", "YN", 11.0) for i in range(1, 25)]
    sessions = [_session(i, kw, f"YN-{i:02d}") for i, kw in enumerate(session_kw, start=1)]
    rules = [
        LoadRule("r1", "YN", LoadRuleType.CRITICAL_REGULATION, threshold_fraction=1.0, reduction_fraction=reduction)
    ]
    return LoadArea(AreaCode("YN"), "Ydre Nørrebro", LoadThresholds(max_capacity_kw=max_kw), chargers, sessions, rules)


def regulate(area: LoadArea) -> bool | None:
    """Drive the regulation cascade the way the application service does."""
    if not area.needs_regulation():
        return None
    area.activate_regulation()
    rounds = 0
    while area.needs_regulation() and rounds < area.MAX_REGULATION_ROUNDS:
        area.reduce_charging_power()
        rounds += 1
    return area.evaluate_regulation_result(rounds)


def test_baseline_is_warning():
    area = make_area([11.0] * 21 + [2.0])  # 233 kW
    assert area.current_load_kw == 233.0
    assert area.status is LoadStatus.WARNING


def test_new_session_pushes_critical_then_regulates_to_stable():
    area = make_area([11.0] * 21 + [2.0])  # 233 kW, 22 sessions
    area.start_session("YN-23", PowerLevel(11.0))

    assert area.current_load_kw == 244.0
    assert area.status is LoadStatus.CRITICAL

    success = regulate(area)
    assert success is True
    assert area.current_load_kw == 219.6  # 244 * 0.90
    assert area.status is LoadStatus.WARNING

    events = [e.event_type for e in area.pull_events()]
    assert events[0] == "ChargingSessionStarted"
    assert "LoadThresholdReached" in events
    assert "LoadRuleActivated" in events
    assert events.count("ChargingPowerReduced") == 23  # one per active session
    assert "LoadAreaStabilized" in events
    assert "RegulationFailed" not in events


def test_unknown_charger_is_rejected():
    area = make_area([11.0])
    with pytest.raises(ValueError):
        area.start_session("ZZ-99", PowerLevel(11.0))


def test_power_above_charger_max_is_rejected():
    area = make_area([11.0])
    with pytest.raises(ValueError):
        area.start_session("YN-05", PowerLevel(22.0))


def test_regulation_failure_emits_regulation_failed():
    # A rule that reduces nothing can never bring load below max -> failure path.
    area = make_area([11.0] * 23, reduction=0.0)  # 253 kW, CRITICAL
    assert area.status is LoadStatus.CRITICAL

    success = regulate(area)
    assert success is False

    events = [e.event_type for e in area.pull_events()]
    assert "RegulationFailed" in events
    assert "LoadAreaStabilized" not in events


def test_restore_power_when_load_drops_below_warning():
    chargers = [Charger("YN-01", "YN", 11.0)]
    reduced = ChargingSession(
        "s1", "YN", "YN-01", PowerLevel(11.0), PowerLevel(9.9), SessionStatus.ACTIVE,
        datetime.now(timezone.utc),
    )
    rules = [LoadRule("r1", "YN", LoadRuleType.CRITICAL_REGULATION, 1.0, 0.10)]
    area = LoadArea(AreaCode("YN"), "YN", LoadThresholds(240.0), chargers, [reduced], rules)

    assert area.current_load_kw == 9.9
    assert area.restore_power_if_stable() is True
    assert area.current_load_kw == 11.0


def test_register_charger_adds_and_emits_event():
    area = make_area([11.0])  # make_area seeds 24 chargers
    charger = area.register_charger("YN-25", 11.0)
    assert charger.charger_id == "YN-25"
    assert area.charger_count == 25
    events = [e.event_type for e in area.pull_events()]
    assert "ChargerRegistered" in events


def test_register_duplicate_charger_rejected():
    area = make_area([11.0])
    with pytest.raises(ValueError):
        area.register_charger("YN-01", 11.0)
