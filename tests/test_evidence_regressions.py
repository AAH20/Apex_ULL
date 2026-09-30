import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("apex_harness", ROOT / "benchmarks/stac/common/harness.py")
harness = importlib.util.module_from_spec(SPEC)
import sys
sys.modules[SPEC.name] = harness
SPEC.loader.exec_module(harness)


def test_jitter_preserves_chronological_order():
    assert harness.compute_latency_stats([1, 100, 1, 100]).jitter_ns == 99
    assert harness.compute_latency_stats([1, 1, 100, 100]).jitter_ns == 33


def test_empty_benchmark_cannot_look_successful():
    with pytest.raises(ValueError):
        harness.run_benchmark("empty", "1", "test", lambda: None, iterations=0)


def test_cost_model_distinguishes_incident_probability_from_downtime_fraction():
    from evaluation.cost.cost_calculator import ULLCostModel
    model = ULLCostModel(downtime_probability=0.005, mean_downtime_hours_per_incident=2, cost_per_hour_downtime=50_000, obsolescence_factor=0)
    assert model.risk_cost == 500
    model.add_component("server", 1, 100_000, 10_000)
    model.revenue_with_ull = 60_000
    assert model.payback_years == pytest.approx(100_000 / 49_500)


def test_synthetic_timing_metadata_is_finalized_after_measurement():
    sys.path.insert(0, str(ROOT / "benchmarks/stac"))
    from stac_t1_tick_to_trade.benchmark import run_stac_t1
    result=run_stac_t1(iterations=10,warmup_iterations=2)
    assert all(value is not None and value>0 for value in result.metadata["sub_stage_timing"].values())
    assert result.metadata["official_stac_result"] is False
    assert "SYNTHETIC" in result.name
