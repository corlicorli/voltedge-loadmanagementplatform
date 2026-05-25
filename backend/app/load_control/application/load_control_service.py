"""LoadControlService — application service orchestrating Load Management.

It loads the aggregate, invokes the relevant command method(s), then drives the
regulation cascade by consulting the four named policies, and finally persists
state and publishes the recorded domain events. The aggregate owns the rules;
this service owns the workflow.
"""
from __future__ import annotations

from typing import Any

from app.load_control.application.commands import (
    CreateLoadArea,
    EvaluateLoadAreaCapacity,
    RegisterCharger,
    StartChargingSession,
)
from app.load_control.application.policies import (
    LoadRegulationPolicy,
    ManualInterventionPolicy,
    PowerReductionPolicy,
    StabilizationPolicy,
)
from app.load_control.application.ports import EventPublisher, InterventionService
from app.load_control.domain.load_area import LoadArea
from app.load_control.domain.repository import LoadAreaAlreadyExists, LoadAreaRepository
from app.load_control.domain.value_objects import (
    AreaCode,
    LoadThresholds,
    PowerLevel,
    ThresholdPercentage,
)


class LoadControlService:
    def __init__(
        self,
        areas: LoadAreaRepository,
        events: EventPublisher,
        interventions: InterventionService,
    ) -> None:
        self._areas = areas
        self._events = events
        self._interventions = interventions

    async def create_load_area(self, cmd: CreateLoadArea) -> str:
        code = AreaCode(cmd.area_code)
        if await self._areas.exists(code):
            raise LoadAreaAlreadyExists(f"Load area '{code.value}' already exists")
        thresholds = LoadThresholds(
            max_capacity_kw=cmd.max_capacity_kw,
            warning=ThresholdPercentage(cmd.warning_fraction),
            critical=ThresholdPercentage(cmd.critical_fraction),
        )
        area = LoadArea.create(code, cmd.area_name, thresholds, cmd.reduction_fraction)
        await self._persist(area)
        return code.value

    async def start_charging_session(self, cmd: StartChargingSession) -> str:
        area = await self._areas.get(AreaCode(cmd.area_code))
        session = area.start_session(cmd.charger_id, PowerLevel(cmd.power_kw))
        await self._regulate_if_needed(area)
        await self._persist(area)
        return session.session_id

    async def evaluate_capacity(self, cmd: EvaluateLoadAreaCapacity) -> None:
        area = await self._areas.get(AreaCode(cmd.area_code))
        area.reassess()
        await self._regulate_if_needed(area)
        await self._persist(area)

    async def register_charger(self, cmd: RegisterCharger) -> dict[str, Any]:
        area = await self._areas.get(AreaCode(cmd.area_code))
        charger = area.register_charger(cmd.charger_id, cmd.max_power_kw)
        await self._persist(area)
        return {
            "charger_id": charger.charger_id,
            "area_code": charger.area_code,
            "max_power_kw": charger.max_power_kw,
            "status": charger.status.value,
        }

    async def _regulate_if_needed(self, area: LoadArea) -> None:
        # LoadRegulationPolicy (on LoadAreaUpdated): activate regulation at/over max.
        if not LoadRegulationPolicy.should_activate(area):
            return
        area.activate_regulation()

        # PowerReductionPolicy (on LoadThresholdReached): reduce 10% per round.
        rounds = 0
        while PowerReductionPolicy.should_reduce(area) and rounds < LoadArea.MAX_REGULATION_ROUNDS:
            area.reduce_charging_power()
            rounds += 1
        area.evaluate_regulation_result(rounds)

        # StabilizationPolicy vs ManualInterventionPolicy (on RegulationResultEvaluated).
        if StabilizationPolicy.is_stable(area):
            return
        if ManualInterventionPolicy.needs_intervention(area):
            await self._interventions.open_request(
                area_code=area.area_code.value,
                reason="Automatic regulation did not bring load below max capacity",
                load_kw=area.current_load_kw,
                max_capacity_kw=area.thresholds.max_capacity_kw,
            )

    async def _persist(self, area: LoadArea) -> None:
        await self._areas.save(area)
        await self._events.publish(area.pull_events())
