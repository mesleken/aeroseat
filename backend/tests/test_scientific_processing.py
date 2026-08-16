import pytest
import numpy as np
from app.domain.contracts.scientific_processing import (
    process_signal, sae_j211_filter,
    ScientificProcessingContractError, SignalProcessingConfigurationError, SignalIntegrityError
)

def test_sae_j211_filter():
    t = np.linspace(0, 0.1, 1001)
    raw_signal = np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 5000 * t)
    filtered = sae_j211_filter(t, raw_signal, cfc=1000)
    assert len(filtered) == len(raw_signal)
    assert np.max(filtered) < np.max(raw_signal)

def test_sae_j211_filter_fft_frequency_attenuation_quantified():
    """Quantitative verification of SAE J211 lowpass filter cutoff attenuation via FFT decibel calculation."""
    t = np.linspace(0, 0.1, 1001) # 10 kHz sample rate
    signal_50hz = np.sin(2 * np.pi * 50 * t)
    noise_3000hz = 0.5 * np.sin(2 * np.pi * 3000 * t)
    raw = signal_50hz + noise_3000hz

    # CFC 1000 cutoff = 1666.7 Hz. 3000 Hz noise is above cutoff (~1.8x fc).
    filtered = sae_j211_filter(t, raw, cfc=1000)

    # Compute FFT Fourier amplitude spectrum |X(f)| at 50 Hz and 3000 Hz
    fft_raw = np.abs(np.fft.rfft(raw))
    fft_filt = np.abs(np.fft.rfft(filtered))
    freqs = np.fft.rfftfreq(len(t), d=0.0001)

    idx_50 = np.argmin(np.abs(freqs - 50.0))
    idx_3000 = np.argmin(np.abs(freqs - 3000.0))

    # Passband (50 Hz): Amplitude ratio preserved > 0.95 (> 95%)
    amplitude_ratio_50hz = fft_filt[idx_50] / fft_raw[idx_50]
    assert amplitude_ratio_50hz > 0.95

    # Stopband (3000 Hz): Amplitude ratio attenuation in decibels: dB = -20 * log10(|X_filt| / |X_raw|)
    amplitude_ratio_3000hz = fft_filt[idx_3000] / fft_raw[idx_3000]
    attenuation_db = -20.0 * np.log10(amplitude_ratio_3000hz)
    assert attenuation_db > 15.0  # Guarantees strictly > 15 dB amplitude attenuation at 3000 Hz

def test_exception_hierarchy_contract_integration():
    """Verifies that catching base ScientificProcessingContractError catches both integrity and configuration errors."""
    assert issubclass(SignalIntegrityError, ScientificProcessingContractError)
    assert issubclass(SignalProcessingConfigurationError, ScientificProcessingContractError)

    t_short = np.linspace(0, 0.001, 5)
    with pytest.raises(ScientificProcessingContractError):
        sae_j211_filter(t_short, np.ones(5), cfc=1000)

def test_sae_j211_filter_short_signal_raises_error():
    t = np.linspace(0, 0.001, 5)
    raw = np.ones(5)
    with pytest.raises(SignalIntegrityError):
        sae_j211_filter(t, raw, cfc=1000)

def test_sae_j211_filter_non_positive_dt_raises_error():
    t = np.zeros(20) # static time vector with dt = 0
    raw = np.ones(20)
    with pytest.raises(SignalIntegrityError):
        sae_j211_filter(t, raw, cfc=1000)

def test_process_signal_determinism():
    t = np.linspace(0, 0.2, 2001).tolist()
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
    t = np.linspace(0, 0.2, 2001).tolist()
    y = (30.0 * np.exp(-((np.array(t) - 0.08)**2) / (2 * 0.02**2))).tolist()
    
    # Strict NO-FALLBACK check: Empty processing_def must raise error
    with pytest.raises(SignalProcessingConfigurationError):
        process_signal(t, y, "head_acceleration", {}, input_unit="SI")

def test_sae_j211_filter_boundary_undersampled_raises_error():
    # CFC 1000 requires fs >= 10,000 Hz. Sample rate 9900 Hz must fail.
    t_undersampled = np.linspace(0, 0.1, 991) # fs = 9900 Hz
    raw_signal = np.sin(2 * np.pi * 50 * t_undersampled)
    with pytest.raises(SignalProcessingConfigurationError) as exc_info:
        sae_j211_filter(t_undersampled, raw_signal, cfc=1000)
    assert "below minimum 10x CFC rate" in str(exc_info.value)

def test_sae_j211_filter_boundary_compliant_passes():
    # CFC 1000 requires fs >= 10,000 Hz. Sample rate 10,000 Hz must pass.
    t_compliant = np.linspace(0, 0.1, 1001) # fs = 10,000 Hz
    raw_signal = np.sin(2 * np.pi * 50 * t_compliant)
    filtered = sae_j211_filter(t_compliant, raw_signal, cfc=1000)
    assert len(filtered) == 1001
