import numpy as np
from scipy.signal import butter, filtfilt

class ScientificProcessingContractError(ValueError):
    """Base exception class for all Contract 1 scientific processing failures."""
    pass

class SignalIntegrityError(ScientificProcessingContractError):
    """Raised when channel signal data integrity check fails (e.g. NaN, Inf, dimension mismatch, non-monotonic time)."""
    pass

class SignalProcessingConfigurationError(ScientificProcessingContractError):
    """Raised when mandatory processing parameters (CFC, threshold_g) are missing from ProcessingDefinition."""
    pass

SAE_J211_TABLE_1_CFC_MAP = {
    "head_acceleration": 1000,
    "sled_acceleration": 60,
    "pelvis_acceleration": 1000,
    "lumbar_force": 1000,
    "lumbar_moment": 1000,
    "femur_force": 600,
    "neck_force": 1000,
    "neck_moment": 600,
    "thorax_spine_acceleration": 180,
    "sternum_acceleration": 1000,
    "chest_deflection": 600,
}

def sae_j211_filter(time_s: np.ndarray, signal_data: np.ndarray, cfc: int) -> np.ndarray:
    """Applies SAE J211-1 / ISO 6487 4-pole phaseless Butterworth digital filter.
    
    Standard SAE J211 specification:
    - 4th-order lowpass Butterworth response (2nd-order bidirectional filtfilt)
    - Cutoff frequency fc = CFC * (5/3) Hz (e.g. CFC 1000 -> fc=1667 Hz, CFC 600 -> fc=1000 Hz, CFC 60 -> fc=100 Hz).
    """
    if len(signal_data) < 10:
        raise SignalIntegrityError("Signal length too short (<10 samples) for SAE J211 Butterworth filtering.")
    
    dt = np.mean(np.diff(time_s))
    if dt <= 0:
        raise SignalIntegrityError("Time vector must be strictly increasing with positive sample interval (dt > 0).")

    sample_rate = 1.0 / dt
    cutoff_hz = cfc * (5.0 / 3.0)
    min_required_fs = 10.0 * cfc  # per SAE J211-1 §5.2 (fs >= 10 * CFC, e.g. 10,000 Hz for CFC 1000)
    if sample_rate < (min_required_fs - 1e-3):
        raise SignalProcessingConfigurationError(
            f"SAE J211 Quality Violation (Binary FAIL): Sample rate ({sample_rate:.1f} Hz) is below minimum 10x CFC rate "
            f"({min_required_fs:.1f} Hz for CFC {cfc}). "
            f"Per SAE J211-1 §5.2 quality requirements, minimum required sampling frequency is fs >= 10 * CFC."
        )
        
    nyquist = 0.5 * sample_rate
    if cutoff_hz >= nyquist:
        raise SignalProcessingConfigurationError(
            f"SAE J211 Invariant Failure: Cutoff frequency ({cutoff_hz:.1f} Hz) exceeds Nyquist limit ({nyquist:.1f} Hz)."
        )

    b, a = butter(2, cutoff_hz / nyquist, btype='lowpass')
    padlen = min(len(signal_data) - 1, 3 * max(len(b), len(a)))
    filtered = filtfilt(b, a, signal_data, padlen=padlen)
    return filtered

def process_signal(
    raw_time_s: list[float] | np.ndarray,
    raw_data: list[float] | np.ndarray,
    channel_name: str,
    processing_def: dict,
    input_unit: str = "SI"
) -> tuple[np.ndarray, np.ndarray]:
    """Applies the mandatory 8-step Scientific Processing Pipeline (Contract 1).
    
    STRICT SINGLE SOURCE OF TRUTH: All processing steps (filter, time_zero, window, resample)
    and their parameters MUST be explicitly defined in processing_def or resolved via mandatory maps.
    Missing mandatory parameters raise SignalProcessingConfigurationError.
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

    # 3. Parameter Extraction from ProcessingDefinition (STRICT NO UNGOVERNED FALLBACK)
    if not processing_def:
        raise SignalProcessingConfigurationError("ProcessingDefinition is empty or not provided.")

    steps_list = processing_def.get("steps", [])
    steps_map = {step.get("step"): step.get("params", {}) for step in steps_list if isinstance(step, dict)}

    # --- Step 4: CFC Extraction & Filter (Strict Table 1 Lookup, No String-Matching Fallback) ---
    filter_params = steps_map.get("filter", {})
    cfc = filter_params.get("channel_frequency_class")
    
    if cfc is None:
        channel_cfcs = filter_params.get("channel_cfc_map", {})
        if isinstance(channel_cfcs, dict):
            cfc = channel_cfcs.get(channel_name)
        if cfc is None:
            cfc = filter_params.get("default_cfc")
        if cfc is None:
            # Exact SAE J211-1 Table 1 Map lookup by channel descriptor key
            cfc = SAE_J211_TABLE_1_CFC_MAP.get(channel_name.lower())
        
    if cfc is None:
        raise SignalProcessingConfigurationError(
            f"Mandatory parameter 'channel_frequency_class' (CFC) for channel '{channel_name}' is missing in ProcessingDefinition."
        )

    if not isinstance(cfc, (int, float)) or cfc <= 0:
        raise SignalProcessingConfigurationError(
            f"Invalid Channel Frequency Class (CFC={cfc}) for channel '{channel_name}' in ProcessingDefinition."
        )

    y_filtered = sae_j211_filter(t, y, int(cfc))

    # --- Step 5: Time-Zero Detection (Systematic physical_quantity, No Heuristic String Matching) ---
    t0_params = steps_map.get("time_zero", {})
    threshold_val = t0_params.get("threshold_val")

    if threshold_val is None:
        threshold_g = t0_params.get("threshold_g")
        if threshold_g is None:
            raise SignalProcessingConfigurationError(
                f"Mandatory time-zero threshold ('threshold_g' or 'threshold_val') missing for channel '{channel_name}'."
            )
        # Systematic physical_quantity check (No fragile string guessing):
        physical_qty = processing_def.get("physical_quantity") or t0_params.get("physical_quantity")
        if physical_qty == "acceleration" or input_unit == "g":
            threshold_val = threshold_g * 9.80665
        else:
            threshold_val = threshold_g

    cross_idx = np.where(np.abs(y_filtered) >= threshold_val)[0]
    if len(cross_idx) == 0:
        raise SignalIntegrityError(
            f"Time-zero detection failed: Signal for channel '{channel_name}' never exceeded threshold value ({threshold_val:.3f})."
        )
    t0 = t[cross_idx[0]]
    t_aligned = t - t0

    # --- Step 6 & 7: Window Selection & Common Analysis Grid ---
    win_params = steps_map.get("window", {})
    resample_params = steps_map.get("resample", {})
    
    t_start_ms = win_params.get("start_offset_ms")
    t_end_ms = win_params.get("end_offset_ms")
    sample_rate_hz = resample_params.get("target_rate_hz")

    if t_start_ms is None or t_end_ms is None or sample_rate_hz is None:
        raise SignalProcessingConfigurationError(
            f"Mandatory window parameters ('start_offset_ms', 'end_offset_ms', 'target_rate_hz') missing in ProcessingDefinition for channel '{channel_name}'."
        )

    t_start = t_start_ms / 1000.0
    t_end = t_end_ms / 1000.0
    
    num_samples = int(round((t_end - t_start) * sample_rate_hz)) + 1
    grid_t = np.linspace(t_start, t_end, num_samples, dtype=np.float64)

    # --- Step 8: Resampling strictly bounded to aligned data range ---
    grid_t = np.clip(grid_t, t_aligned[0], t_aligned[-1])
    grid_y = np.interp(grid_t, t_aligned, y_filtered)

    return grid_t, grid_y
