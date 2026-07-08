"""Model artifact assertions (Step 2)."""
import json
import warnings

import pytest

from app import ml


@pytest.fixture(scope="module")
def metrics():
    if not ml.METRICS.exists():
        pytest.skip("metrics.json not built; run train scripts first")
    return json.loads(ml.METRICS.read_text(encoding="utf-8"))


def test_metrics_file_exists(metrics):
    assert "congestion" in metrics
    assert "route_difficulty" in metrics


def test_model_artifacts_present():
    assert ml.CONGESTION_MODEL.exists()
    assert ml.ROUTE_MODEL.exists()
    assert ml.CONGESTION_META.exists()
    assert ml.ROUTE_META.exists()


def test_congestion_mae_recorded(metrics):
    assert metrics["congestion"]["valid_mae"] > 0


def test_route_macro_f1(metrics):
    f1 = metrics["route_difficulty"]["cv_macro_f1"]
    # spec: warn instead of fail if <= 0.6
    if f1 <= 0.6:
        warnings.warn(f"route macro-F1 {f1} <= 0.6")
    assert f1 > 0  # sanity


def test_route_meta_classes():
    meta = ml.load_meta(ml.ROUTE_META)
    assert meta["classes"] == ["단순", "보통", "복잡", "이동 불가"]
