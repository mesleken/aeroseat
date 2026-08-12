import numpy as np

def calculate_sprague_geers(sim_signal: np.ndarray, test_signal: np.ndarray) -> tuple[float, float, float]:
    """Calculates Sprague-Geers Magnitude Error (M), Phase Error (P), and Combined Error (C).
    
    References SAE ARP5765B methodology.
    """
    c = np.array(test_signal, dtype=np.float64)
    m = np.array(sim_signal, dtype=np.float64)
    
    sum_c2 = np.sum(c**2)
    sum_m2 = np.sum(m**2)
    sum_mc = np.sum(m * c)
    
    if sum_c2 == 0 or sum_m2 == 0:
        return 0.0, 0.0, 0.0
    
    # Magnitude Error M
    magnitude_error = np.sqrt(sum_m2 / sum_c2) - 1.0
    
    # Phase Error P
    cos_theta = sum_mc / np.sqrt(sum_m2 * sum_c2)
    cos_theta = np.clip(cos_theta, -1.0, 1.0) # Numerical safety
    phase_error = (1.0 / np.pi) * np.arccos(cos_theta)
    
    # Combined Error C
    combined_error = np.sqrt(magnitude_error**2 + phase_error**2)
    
    return float(magnitude_error), float(phase_error), float(combined_error)

def calculate_channel_correlation_vector(
    time_grid: np.ndarray,
    sim_signal: np.ndarray,
    test_signal: np.ndarray,
    channel_name: str
) -> dict:
    """Computes full correlation metric vector for a single channel (Contract 2)."""
    m = np.array(sim_signal, dtype=np.float64)
    c = np.array(test_signal, dtype=np.float64)
    t = np.array(time_grid, dtype=np.float64)

    mag_err, phase_err, sg_combined = calculate_sprague_geers(m, c)
    
    # Peak error
    peak_sim = np.max(np.abs(m))
    peak_test = np.max(np.abs(c))
    peak_error = float(np.abs(peak_sim - peak_test) / (peak_test if peak_test > 1e-6 else 1.0))
    
    # Time-to-peak error (in ms)
    idx_sim = np.argmax(np.abs(m))
    idx_test = np.argmax(np.abs(c))
    t_to_peak_err_ms = float((t[idx_sim] - t[idx_test]) * 1000.0)
    
    # RMS error normalized by peak-to-peak range
    range_test = np.ptp(c) if np.ptp(c) > 1e-6 else 1.0
    rms_err = float(np.sqrt(np.mean((m - c)**2)) / range_test)
    
    return {
        "channel": channel_name,
        "magnitude_error": round(mag_err, 4),
        "phase_error_ms": round(t_to_peak_err_ms, 2),
        "shape_metric_sprague_geers": round(sg_combined, 4),
        "sprague_geers_phase": round(phase_err, 4),
        "peak_error": round(peak_error, 4),
        "rms_error": round(rms_err, 4)
    }
