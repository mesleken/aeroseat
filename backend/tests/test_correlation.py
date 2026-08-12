import pytest
import numpy as np
from app.domain.contracts.correlation import calculate_sprague_geers, calculate_channel_correlation_vector

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
