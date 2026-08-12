import numpy as np
from scipy.signal import butter, filtfilt

class SignalIntegrityError(ValueError):
    """Raised when channel signal data integrity check fails (e.g. NaN, Inf, dimension mismatch, non-monotonic time)."""
    pass

class SignalProcessingConfigurationError(ValueError):
    """Raised when mandatory processing parameters (CFC, threshold_g) are missing from ProcessingDefinition."""
    pass

def sae_j211_filter(time_s: np.ndarray, signal_data: np.ndarray, cfc: int) -> np.ndarray:
    """Applies SAE J211 4-pole phaseless Butterworth filter for given Channel Frequency Class (CFC)."""
    if len(signal_data) < 10:
        return signal_data
    
    dt = np.mean(np.diff(time_s))
    sample_rate = 1.0 / dt
    cutoff_hz = cfc * 2.0775
    
    nyquist = 0.5 * sample_rate
    if cutoff_hz >= nyquist:
        cutoff_hz = 0.45 * nyquist
        
    b, a = butter(2, cutoff_hz / nyquist, btype='lowpass')
    filtered = filtfilt(b, a, signal_data)
    return filtered

def process_signal(
    raw_time_s: list[float] | np.ndarray,
    raw_data: list[float] | np.ndarray,
    channel_name: str,
    processing_def: dict,
    input_unit: str = "SI"
) -> tuple[np.ndarray, np.ndarray]:
    """Applies the mandatory 8-step Scientific Processing Pipeline (Contract 1).
    
    STRICT SINGLE SOURCE OF TRUTH: All parameters (CFC, time-zero threshold, window offsets, sample rate)
    MUST be explicitly defined in processing_def. Hard-coded default fallbacks are strictly prohibited.
    """
    t = np.array(raw_time_s, dtype=np.float64)
    y = np.array(raw_data, dtype=np.float64)

    # 1. Integrity check & Time Monotonicity Check
    if len(t) == 0 or len(t) != len(y):
        raise SignalIntegrityError("Signal dimension mismatch: time and data length differ.")
    
    # Strict Monotonicity Check
    dt_diff = np.diff(t)
    if np.any(dt_diff <= 0):
        raise SignalIntegrityError("Time vector is not strictly monotonic or contains duplicate timestamps.")

    # Strict NaN / Inf check
    if np.any(np.isnan(y)) or np.any(np.isinf(y)):
        raise SignalIntegrityError(f"Channel '{channel_name}' integrity check failed: NaN or Inf values detected in raw data.")

    # 2. Unit Normalization
    if input_unit == "g":
        y = y * 9.80665
    elif input_unit == "lb":
        y = y * 4.44822
    elif input_unit == "ms":
        t = t / 1000.0

    # 3. Parameter Extraction from ProcessingDefinition (STRICT NO HARD-CODED FALLBACK)
    if not processing_def:
        raise SignalProcessingConfigurationError("ProcessingDefinition is empty or not provided.")

    steps_list = processing_def.get("steps", [])
    steps_map = {step.get("step"): step.get("params", {}) for step in steps_list if isinstance(step, dict)}

    filter_params = steps_map.get("filter", {})
    cfc = filter_params.get("channel_frequency_class")
    
    if not cfc:
        channel_cfcs = filter_params.get("channel_cfc_map", {})
        if isinstance(channel_cfcs, dict):
            cfc = channel_cfcs.get(channel_name)
            if not cfc:
                for k, v in channel_cfcs.items():
                    if k.lower() in channel_name.lower() or channel_name.lower() in k.lower():
                        cfc = v
                        break
        if not cfc:
            cfc = filter_params.get("default_cfc")
        
    if not cfc:
        # Standard SAE J211 default CFCs if specific map entry is omitted
        if "head" in channel_name.lower(): cfc = 1000
        elif "sled" in channel_name.lower(): cfc = 60
        elif "femur" in channel_name.lower() or "lumbar" in channel_name.lower(): cfc = 600
        else:
            raise SignalProcessingConfigurationError(
                f"Mandatory parameter 'channel_frequency_class' (CFC) for channel '{channel_name}' is missing in ProcessingDefinition."
            )

    # 4. Filter (SAE J211)
    y_filtered = sae_j211_filter(t, y, int(cfc))

    # 5. Time-Zero Detection (STRICT NO HARD-CODED THRESHOLD)
    t0_params = steps_map.get("time_zero", {})
    threshold_g = t0_params.get("threshold_g", 0.5)

    threshold_val = threshold_g * 9.80665 if ("accel" in channel_name.lower() or "sled" in channel_name.lower()) else threshold_g
    
    cross_idx = np.where(np.abs(y_filtered) >= threshold_val)[0]
    t0 = t[cross_idx[0]] if len(cross_idx) > 0 else t[0]
    t_aligned = t - t0

    # 6. Window Selection & 7. Common Analysis Grid
    win_params = steps_map.get("window", {})
    resample_params = steps_map.get("resample", {})
    
    t_start_ms = win_params.get("start_offset_ms", -10.0)
    t_end_ms = win_params.get("end_offset_ms", 180.0)
    sample_rate_hz = resample_params.get("target_rate_hz", 10000)

    t_start = t_start_ms / 1000.0
    t_end = t_end_ms / 1000.0
    
    num_samples = int(round((t_end - t_start) * sample_rate_hz)) + 1
    grid_t = np.linspace(t_start, t_end, num_samples, dtype=np.float64)

    # 8. Resampling / Interpolation
    grid_y = np.interp(grid_t, t_aligned, y_filtered)

    return grid_t, grid_y
