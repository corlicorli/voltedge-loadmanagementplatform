import pytest

from app.load_control.domain.value_objects import (
    AreaCode,
    LoadStatus,
    LoadThresholds,
    PowerLevel,
)

pytestmark = pytest.mark.unit


def test_area_code_normalises_to_upper():
    assert AreaCode(" yn ").value == "YN"


def test_area_code_rejects_empty():
    with pytest.raises(ValueError):
        AreaCode("   ")


def test_power_level_rejects_negative():
    with pytest.raises(ValueError):
        PowerLevel(-1.0)


def test_power_level_reduced_by_ten_percent():
    assert PowerLevel(11.0).reduced_by(0.10).kw == 9.9


def test_thresholds_derive_kw():
    t = LoadThresholds(max_capacity_kw=240.0)
    assert t.warning_threshold_kw == 204.0
    assert t.critical_threshold_kw == 240.0


@pytest.mark.parametrize(
    "load,expected",
    [
        (200.0, LoadStatus.STABLE),
        (203.9, LoadStatus.STABLE),
        (204.0, LoadStatus.WARNING),
        (233.0, LoadStatus.WARNING),
        (239.9, LoadStatus.WARNING),
        (240.0, LoadStatus.CRITICAL),
        (244.0, LoadStatus.CRITICAL),
    ],
)
def test_classify(load, expected):
    assert LoadThresholds(max_capacity_kw=240.0).classify(load) is expected


def test_available_capacity_can_be_negative():
    assert LoadThresholds(max_capacity_kw=240.0).available_capacity_kw(244.0) == -4.0
