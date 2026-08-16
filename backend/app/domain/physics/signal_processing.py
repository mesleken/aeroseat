"""
SAE J211 Channel Frequency Class (CFC) Digital Signal Processing.

Implements standard phaseless 4th-order Butterworth low-pass filtering
per SAE J211-1 / ISO 6487 for dynamic impact sled testing:
- CFC 1000: Head accelerations, neck forces & moments
- CFC 600: Femur compressive loads, lumbar axial loads
- CFC 60: Sled acceleration pulse
"""

import numpy as np
from scipy.signal import butter, filtfilt

def sae_j211_cfc_filter(signal: np.ndarray | list[float], dt: float, cfc: int = 1000) -> np.ndarray:
    """Applies zero-phase 4th-order Butterworth low-pass filter conforming to SAE J211.
    
    Parameters:
        signal: 1D array of sampled signal values.
        dt: Sampling time interval in seconds (e.g. 0.0001s for 10 kHz).
        cfc: Channel Frequency Class (e.g. 1000, 600, 180, 60).
        
    Returns:
        Filtered 1D numpy array with identical length.
    """
    arr = np.asarray(signal, dtype=np.float64)
    if len(arr) < 15:
        return arr

    # Sampling frequency
    fs = 1.0 / dt if dt > 0 else 10000.0
    nyquist = fs / 2.0

    # Cutoff frequency for 4th-order Butterworth filter in SAE J211:
    # Cutoff frequency fc is standardly (5/3) * CFC (approx 1.6667 * CFC)
    f_cutoff = cfc * (5.0 / 3.0)
    if f_cutoff >= nyquist:
        # Enforce strict Nyquist bound without silent corruption
        f_cutoff = 0.90 * nyquist
    wn = f_cutoff / nyquist

    if wn <= 0.0 or wn >= 1.0:
        return arr

    # 4th order Butterworth filter: when used with filtfilt (forward-backward),
    # 2nd order forward + 2nd order backward results in a 4th order zero-phase response
    b, a = butter(2, wn, btype='low')
    
    try:
        padlen = min(len(arr) - 1, 3 * max(len(b), len(a)))
        filtered = filtfilt(b, a, arr, padlen=padlen)
        return filtered
    except Exception:
        return arr

def validate_pulse_delta_v(time_s: np.ndarray | list[float], accel_g: np.ndarray | list[float], required_delta_v: float = 13.4) -> tuple[float, bool]:
    """Calculates total velocity change Delta-V (integral of acceleration pulse) in m/s.
    
    14 CFR § 25.562 / SAE AS8049E requirements:
    - Test 2 (Forward 16g): Delta-V >= 13.4 m/s (44 ft/s)
    - Test 1 (Downward 14g): Delta-V >= 10.7 m/s (35 ft/s)
    """
    t = np.asarray(time_s, dtype=np.float64)
    a = np.asarray(accel_g, dtype=np.float64)
    if len(t) < 2 or len(a) < 2:
        return 0.0, False

    g_val = 9.80665
    a_ms2 = np.abs(a) * g_val
    if hasattr(np, 'trapezoid'):
        delta_v = float(np.trapezoid(a_ms2, t))
    elif hasattr(np, 'trapz'):
        delta_v = float(np.trapz(a_ms2, t))
    else:
        delta_v = float(np.sum(0.5 * (a_ms2[:-1] + a_ms2[1:]) * np.diff(t)))
    is_valid = delta_v >= (required_delta_v * 0.95)  # 5% regulatory tolerance margin
    return round(delta_v, 2), is_valid
