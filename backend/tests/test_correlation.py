import os
import tempfile
import pytest
import numpy as np
from app.domain.contracts.correlation import calculate_sprague_geers, calculate_channel_correlation_vector
from app.api.v1.endpoints.correlation import load_physical_test_signal
from app.domain.contracts.golden_dataset import run_golden_dataset_regression

def test_sprague_geers_identical_signals():
    sig = np.sin(np.linspace(0, np.pi, 100))
    m, p, c = calculate_sprague_geers(sig, sig)
    assert abs(m) < 1e-5
    assert abs(p) < 1e-5
    assert abs(c) < 1e-5

def test_correlation_vector_generation():
    t = np.linspace(-0.010, 0.180, 1901)
    sim = 40.0 * np.exp(-((t - 0.075)**2) / (2 * 0.02**2))
    test = 42.0 * np.exp(-((t - 0.076)**2) / (2 * 0.02**2))
    
    vec = calculate_channel_correlation_vector(t, sim, test, "head_acceleration")
    assert vec["channel"] == "head_acceleration"
    assert "magnitude_error" in vec
    assert "phase_error_ms" in vec
    assert "shape_metric_sprague_geers" in vec
    assert "peak_error" in vec

def test_load_real_physical_test_csv():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("time_s,head_acceleration_g,femur_load_kn,lumbar_load_kn\n")
        f.write("0.000,0.0,0.0,0.0\n")
        f.write("0.010,1.2,0.1,0.2\n")
        f.write("0.020,5.8,0.5,0.8\n")
        f.write("0.030,12.4,1.2,1.5\n")
        f.write("0.040,25.0,2.5,2.8\n")
        f.write("0.050,42.1,4.2,3.5\n")
        temp_path = f.name

    try:
        data = load_physical_test_signal(temp_path)
        assert len(data["time_s"]) == 6
        assert len(data["head_acceleration"]) == 6
        assert data["head_acceleration"][-1] == 42.1
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_golden_dataset_smoke_test():
    res = run_golden_dataset_regression()
    assert "SMOKE_TEST_PASS" in res["status"]
    assert res["layer2_correlation"]["regression_status"] == "SMOKE_TEST_PASS"
