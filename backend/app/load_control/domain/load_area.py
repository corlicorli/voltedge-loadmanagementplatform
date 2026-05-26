"""LoadArea — Aggregate Root for the Load Control Context.

All invariants around load, status and regulation are enforced here, inside one
transactional boundary. State changes happen ONLY through aggregate methods,
each of which records the domain events the application layer later publishes.

The method names mirror the commands from the event storming:
    start_session            -> ChargingSessionStarted, LoadAreaUpdated, LoadThresholdReached
    activate_regulation      -> LoadRuleActivated
    reduce_charging_power    -> ChargingPowerReduced (per session), CurrentLoadUpdated
    evaluate_regulation_result -> RegulationResultEvaluated, LoadAreaStabilized | RegulationFailed
    restore_power_if_stable  -> CurrentLoadUpdated (Business Rule 5)
"""
from __future__ import annotations

import uuid

from app.load_control.domain.entities import (
    Charger,
    ChargerConnectivity,
    ChargerStatus,
    ChargingSession,
    LoadAdjustment,
    LoadRule,
    LoadRuleType,
    SessionStatus,
)
from app.load_control.domain.events import (
    ChargerCameOnline,
    ChargerRegistered,
    ChargingPowerReduced,
    ChargingSessionStarted,
    CurrentLoadUpdated,
    LoadAreaStabilized,
    LoadAreaUpdated,
    LoadRuleActivated,
    LoadThresholdReached,
    RegulationFailed,
    RegulationResultEvaluated,
)
from app.load_control.domain.value_objects import (
    AreaCode,
    LoadStatus,
    LoadThresholds,
    PowerLevel,
)
from app.shared.domain_event import DomainEvent, utcnow


class LoadArea:
    """Aggregate root governing one geographically/technically bounded load area."""

    MAX_REGULATION_ROUNDS = 5

    def __init__(
        self,
        area_code: AreaCode,
        area_name: str,
        thresholds: LoadThresholds,
        chargers: list[Charger],
        sessions: list[ChargingSession],
        rules: list[LoadRule],
        status: LoadStatus | None = None,
    ) -> None:
        self.area_code = area_code
        self.area_name = area_name
        self.thresholds = thresholds
        self._chargers: dict[str, Charger] = {c.charger_id: c for c in chargers}
        self._sessions: dict[str, ChargingSession] = {s.session_id: s for s in sessions}
        self._rules: list[LoadRule] = list(rules)
        self._events: list[DomainEvent] = []
        self._adjustments: list[LoadAdjustment] = []
        self.status = status or self.thresholds.classify(self.current_load_kw)

    # ----- factory: CreateLoadArea ------------------------------------------

    @classmethod
    def create(
        cls,
        area_code: AreaCode,
        area_name: str,
        thresholds: LoadThresholds,
        reduction_fraction: float = 0.10,
    ) -> LoadArea:
        """Factory for a brand-new, empty LoadArea with its default load rules
        (CRITICAL_REGULATION + WARNING_LIMIT). No chargers or sessions yet — those
        are added through the API during onboarding."""
        rules = [
            LoadRule(
                rule_id=str(uuid.uuid4()),
                area_code=area_code.value,
                rule_type=LoadRuleType.CRITICAL_REGULATION,
                threshold_fraction=thresholds.critical.fraction,
                reduction_fraction=reduction_fraction,
                active=True,
            ),
            LoadRule(
                rule_id=str(uuid.uuid4()),
                area_code=area_code.value,
                rule_type=LoadRuleType.WARNING_LIMIT,
                threshold_fraction=thresholds.warning.fraction,
                reduction_fraction=0.0,
                active=True,
            ),
        ]
        return cls(
            area_code=area_code,
            area_name=area_name,
            thresholds=thresholds,
            chargers=[],
            sessions=[],
            rules=rules,
            status=LoadStatus.STABLE,
        )

    # ----- derived state ----------------------------------------------------

    @property
    def active_sessions(self) -> list[ChargingSession]:
        return [s for s in self._sessions.values() if s.is_active]

    @property
    def current_load_kw(self) -> float:
        return round(sum(s.current_power.kw for s in self.active_sessions), 3)

    @property
    def available_capacity_kw(self) -> float:
        return self.thresholds.available_capacity_kw(self.current_load_kw)

    @property
    def active_session_count(self) -> int:
        return len(self.active_sessions)

    @property
    def charger_count(self) -> int:
        return len(self._chargers)

    # ----- command: RegisterCharger -----------------------------------------

    def register_charger(self, charger_id: str, max_power_kw: float, name: str = "") -> Charger:
        if charger_id in self._chargers:
            raise ValueError(f"Charger {charger_id!r} already exists in area {self.area_code}")
        if max_power_kw <= 0:
            raise ValueError("Charger max power must be positive")
        charger = Charger(
            charger_id=charger_id,
            area_code=self.area_code.value,
            max_power_kw=max_power_kw,
            name=name or charger_id,
            status=ChargerStatus.AVAILABLE,
            last_seen_at=utcnow(),
        )
        self._chargers[charger_id] = charger
        self._record(
            ChargerRegistered(
                area_code=self.area_code.value,
                charger_id=charger_id,
                max_power_kw=max_power_kw,
                name=charger.name,
            )
        )
        return charger

    def record_charger_heartbeat(self, charger_id: str) -> Charger:
        """A charger reports in (online). Refreshes last_seen and records
        ChargerCameOnline on an offline->online transition."""
        if charger_id not in self._chargers:
            raise ValueError(f"Charger {charger_id!r} is not part of area {self.area_code}")
        now = utcnow()
        charger = self._chargers[charger_id]
        was_online = charger.connectivity(now) is ChargerConnectivity.ONLINE
        updated = charger.with_heartbeat(now)
        self._chargers[charger_id] = updated
        if not was_online:
            self._record(ChargerCameOnline(area_code=self.area_code.value, charger_id=charger_id))
        return updated

    # ----- command: StartChargingSession ------------------------------------

    def start_session(self, charger_id: str, requested_power: PowerLevel) -> ChargingSession:
        if charger_id not in self._chargers:
            raise ValueError(f"Charger {charger_id!r} is not part of area {self.area_code}")
        charger = self._chargers[charger_id]
        if requested_power.kw > charger.max_power_kw:
            raise ValueError(
                f"Requested {requested_power.kw} kW exceeds charger max {charger.max_power_kw} kW"
            )

        session = ChargingSession(
            session_id=str(uuid.uuid4()),
            area_code=self.area_code.value,
            charger_id=charger_id,
            requested_power=requested_power,
            current_power=requested_power,
            status=SessionStatus.ACTIVE,
            started_at=utcnow(),
        )
        self._sessions[session.session_id] = session
        self._record(
            ChargingSessionStarted(
                area_code=self.area_code.value,
                session_id=session.session_id,
                charger_id=charger_id,
                power_kw=requested_power.kw,
            )
        )
        self._update_load()
        self._evaluate_capacity()
        return session

    # ----- command: UpdateCurrentLoad ---------------------------------------

    def _update_load(self) -> None:
        self.status = self.thresholds.classify(self.current_load_kw)
        self._record(
            LoadAreaUpdated(
                area_code=self.area_code.value,
                current_load_kw=self.current_load_kw,
                available_capacity_kw=self.available_capacity_kw,
                status=self.status.value,
                active_session_count=self.active_session_count,
            )
        )

    # ----- command: EvaluateLoadAreaCapacity --------------------------------

    def _evaluate_capacity(self) -> None:
        if self.status is LoadStatus.STABLE:
            return
        threshold_kw = (
            self.thresholds.critical_threshold_kw
            if self.status is LoadStatus.CRITICAL
            else self.thresholds.warning_threshold_kw
        )
        self._record(
            LoadThresholdReached(
                area_code=self.area_code.value,
                current_load_kw=self.current_load_kw,
                threshold_kw=threshold_kw,
                status=self.status.value,
            )
        )

    def reassess(self) -> None:
        """Recompute load and re-evaluate capacity (the EvaluateLoadAreaCapacity command)."""
        self._update_load()
        self._evaluate_capacity()

    def needs_regulation(self) -> bool:
        """True when load is at/above the critical threshold (Business Rule 3)."""
        return self.status is LoadStatus.CRITICAL

    # ----- command: ActivateLoadRule ----------------------------------------

    def activate_regulation(self) -> LoadRule:
        rule = self._critical_rule()
        self._record(
            LoadRuleActivated(
                area_code=self.area_code.value,
                rule_id=rule.rule_id,
                rule_type=rule.rule_type.value,
                reduction_pct=round(rule.reduction_fraction * 100, 2),
            )
        )
        return rule

    def _critical_rule(self) -> LoadRule:
        for rule in self._rules:
            if rule.active and rule.rule_type is LoadRuleType.CRITICAL_REGULATION:
                return rule
        raise ValueError(f"No active CRITICAL_REGULATION rule for area {self.area_code}")

    # ----- command: ReduceChargingPower + RecalculateCurrentLoad ------------

    def reduce_charging_power(self) -> list[LoadAdjustment]:
        rule = self._critical_rule()
        fraction = rule.reduction_fraction
        made: list[LoadAdjustment] = []
        for session in self.active_sessions:
            previous_power = session.current_power
            updated = session.reduce_power(fraction)
            self._sessions[session.session_id] = updated
            adjustment = LoadAdjustment(
                adjustment_id=str(uuid.uuid4()),
                area_code=self.area_code.value,
                session_id=session.session_id,
                previous_power_kw=previous_power.kw,
                new_power_kw=updated.current_power.kw,
                reason=f"{rule.rule_type.value}: reduce {round(fraction * 100)}%",
                created_at=utcnow(),
            )
            self._adjustments.append(adjustment)
            made.append(adjustment)
            self._record(
                ChargingPowerReduced(
                    area_code=self.area_code.value,
                    session_id=session.session_id,
                    previous_power_kw=previous_power.kw,
                    new_power_kw=updated.current_power.kw,
                )
            )
        self._recalculate()
        return made

    def _recalculate(self) -> None:
        self.status = self.thresholds.classify(self.current_load_kw)
        self._record(
            CurrentLoadUpdated(
                area_code=self.area_code.value,
                current_load_kw=self.current_load_kw,
                available_capacity_kw=self.available_capacity_kw,
                status=self.status.value,
                active_session_count=self.active_session_count,
            )
        )

    # ----- command: EvaluateRegulationResult --------------------------------

    def evaluate_regulation_result(self, rounds: int) -> bool:
        success = self.current_load_kw < self.thresholds.critical_threshold_kw
        self._record(
            RegulationResultEvaluated(
                area_code=self.area_code.value,
                current_load_kw=self.current_load_kw,
                max_capacity_kw=self.thresholds.max_capacity_kw,
                success=success,
                rounds=rounds,
            )
        )
        if success:
            self._record(
                LoadAreaStabilized(
                    area_code=self.area_code.value,
                    current_load_kw=self.current_load_kw,
                    status=self.status.value,
                )
            )
        else:
            self._record(
                RegulationFailed(
                    area_code=self.area_code.value,
                    current_load_kw=self.current_load_kw,
                    max_capacity_kw=self.thresholds.max_capacity_kw,
                )
            )
        return success

    # ----- command: restore power (Business Rule 5) -------------------------

    def restore_power_if_stable(self) -> bool:
        """If load is below the warning threshold, restore sessions to full power."""
        if self.thresholds.classify(self.current_load_kw) is not LoadStatus.STABLE:
            return False
        changed = False
        for session in self.active_sessions:
            if session.current_power.kw < session.requested_power.kw:
                self._sessions[session.session_id] = session.restore_power()
                changed = True
        if changed:
            self._recalculate()
        return changed

    # ----- event plumbing ---------------------------------------------------

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    # ----- read accessors for persistence/projections ----------------------

    @property
    def adjustments(self) -> list[LoadAdjustment]:
        return list(self._adjustments)

    @property
    def sessions(self) -> list[ChargingSession]:
        return list(self._sessions.values())

    @property
    def chargers(self) -> list[Charger]:
        return list(self._chargers.values())

    @property
    def rules(self) -> list[LoadRule]:
        return list(self._rules)
