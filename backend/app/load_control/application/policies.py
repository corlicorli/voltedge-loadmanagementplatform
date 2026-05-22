"""The four named policies from the event storming.

A policy is a business rule that automatically triggers a command in reaction to
a domain event. They are modelled here as explicit, documented decision objects
that the LoadControlService consults while orchestrating the regulation cascade,
so the design's policies are visible 1:1 in the code.
"""
from __future__ import annotations

from app.load_control.domain.load_area import LoadArea


class LoadRegulationPolicy:
    """Trigger: LoadAreaUpdated.
    Rule: if current load reaches max capacity, activate load regulation.
    """

    @staticmethod
    def should_activate(area: LoadArea) -> bool:
        return area.needs_regulation()


class PowerReductionPolicy:
    """Trigger: LoadThresholdReached.
    Rule: if the load threshold is reached, reduce charging power by 10%
    (repeated until below max capacity or the max number of rounds is hit).
    """

    @staticmethod
    def should_reduce(area: LoadArea) -> bool:
        return area.needs_regulation()


class StabilizationPolicy:
    """Trigger: RegulationResultEvaluated.
    Rule: if current load is below max capacity, mark the load area as stable.
    """

    @staticmethod
    def is_stable(area: LoadArea) -> bool:
        return area.current_load_kw < area.thresholds.critical_threshold_kw


class ManualInterventionPolicy:
    """Trigger: RegulationResultEvaluated.
    Rule: if load is still above max capacity after regulation, create a manual
    intervention request (notifying an ExternalTechnician).
    """

    @staticmethod
    def needs_intervention(area: LoadArea) -> bool:
        return area.current_load_kw >= area.thresholds.critical_threshold_kw
