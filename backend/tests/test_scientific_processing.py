import pytest
import numpy as np
from app.domain.contracts.scientific_processing import process_signal, sae_j211_filter, SignalProcessingConfigurationError

def test_sae_j211_filter():
    t = np.linspace(0, 0.1, 1000)
    raw_signal = np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 5000 * t)
    filtered = sae_j211_filter(t, raw_signal, cfc=1000)
    assert len(filtered) == len(raw_signal)
    assert np.max(filtered) < np.max(raw_signal)

def test_process_signal_determinism():
    t = np.linspace(0, 0.2, 2000).tolist()
    y = (30.0 * np.exp(-((np.array(t) - 0.08)**2) / (2 * 0.02**2))).tolist()
    
    proc_def = {
        "steps": [
            {"step": "filter", "params": {"channel_frequency_class": 1000}},
            {"step": "time_zero", "params": {"threshold_g": 0.5}},
            {"step": "window", "params": {"start_offset_ms": -10.0, "end_offset_ms": 180.0}},
            {"step": "resample", "params": {"target_rate_hz": 10000}}
        ]
    }

    t1, y1 = process_signal(t, y, "head_acceleration", proc_def, input_unit="SI")
    t2, y2 = process_signal(t, y, "head_acceleration", proc_def, input_unit="SI")
    
    # Contract 1 Guarantee: Bit-for-bit determinism
    np.testing.assert_array_equal(t1, t2)
    np.testing.assert_array_equal(y1, y2)

def test_missing_processing_definition_raises_error():
    t = np.linspace(0, 0.2, 2000).tolist()
    y = (30.0 * np.exp(-((np.array(t) - 0.08)**2) / (2 * 0.02**2))).tolist()
    
    # Strict NO-FALLBACK check: Empty processing_def must raise error
    with pytest.raises(SignalProcessingConfigurationError):
        process_signal(t, y, "head_acceleration", {}, input_unit="SI")
