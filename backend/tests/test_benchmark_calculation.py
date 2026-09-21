from app.models.schemas import BenchmarkSideResult
from app.benchmark.benchmark_service import NOISE_THRESHOLD_PERCENT


def test_noise_threshold_is_reasonable():
    assert 0 < NOISE_THRESHOLD_PERCENT < 20


def test_improvement_formula():
    original = 2.0
    optimized = 1.0
    improvement = ((original - optimized) / original) * 100
    assert improvement == 50.0
