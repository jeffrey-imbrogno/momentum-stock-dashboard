from config import ScannerConfig
from scanner.models import PivotResult
from scanner.pivots import calculate_entry
from scanner.trade_planner import calculate_position_size, calculate_stop_plan, calculate_targets


def test_entry_buffer_calculation():
    config = ScannerConfig(entry_buffer=0.001)

    assert calculate_entry(100.0, config) == 100.1


def test_targets_and_position_sizing():
    target_2r, target_3r = calculate_targets(100.0, 95.0)
    shares, position_value, dollar_risk = calculate_position_size(100.0, 95.0, 100_000, 0.005)

    assert target_2r == 110.0
    assert target_3r == 115.0
    assert shares == 100
    assert position_value == 10_000
    assert dollar_risk == 500


def test_stop_plan_uses_structural_stop(make_trending_history):
    history = make_trending_history(start=80, end=110)
    pivot = PivotResult("VCP PIVOT", pivot=108.0, entry=108.108, valid_setup=True, confidence=80)
    plan = calculate_stop_plan(history, pivot, ScannerConfig())

    assert plan.stop is not None
    assert plan.risk_per_share is not None
    assert plan.target_2r is not None
    assert plan.shares > 0
