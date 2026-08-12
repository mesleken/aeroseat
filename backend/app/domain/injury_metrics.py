import numpy as np

def calculate_hic15(time_s: np.ndarray, accel_g: np.ndarray) -> float | None:
    """Calculates HIC15 (Head Injury Criterion over 15ms window max).
    
    Returns None if signal data is invalid or empty.
    """
    t = np.array(time_s, dtype=np.float64)
    a = np.array(accel_g, dtype=np.float64)
    
    n = len(t)
    if n < 10 or np.all(a == 0):
        return None
    
    max_hic = 0.0
    dt = np.mean(np.diff(t))
    if dt <= 0:
        return None
    
    # Cumulative trapezoidal integration
    cum_a = np.zeros(n, dtype=np.float64)
    for k in range(1, n):
        cum_a[k] = cum_a[k-1] + 0.5 * (a[k] + a[k-1]) * (t[k] - t[k-1])
    
    max_samples_15ms = int(round(0.015 / dt)) + 1
    
    for i in range(n):
        for j in range(i + 1, min(i + max_samples_15ms, n)):
            delta_t = t[j] - t[i]
            if delta_t <= 0.0 or delta_t > 0.015:
                continue
            
            avg_a = (cum_a[j] - cum_a[i]) / delta_t
            if avg_a <= 0:
                continue
                
            hic_val = (avg_a ** 2.5) * delta_t
            if hic_val > max_hic:
                max_hic = hic_val

    return float(round(max_hic, 1))

def calculate_nij(fz_n: np.ndarray, my_nm: np.ndarray) -> tuple[float | None, str | None]:
    """Calculates Nij for FAA Hybrid III 50th Male Dummy across 4 neck injury modes."""
    fz = np.array(fz_n, dtype=np.float64)
    my = np.array(my_nm, dtype=np.float64)
    
    if len(fz) == 0 or len(my) == 0:
        return None, None

    f_tension_crit = 6811.0
    f_compression_crit = 6160.0
    m_flexion_crit = 310.0
    m_extension_crit = 135.0

    nij_tf = np.maximum(0, fz / f_tension_crit) + np.maximum(0, my / m_flexion_crit)
    nij_te = np.maximum(0, fz / f_tension_crit) + np.maximum(0, -my / m_extension_crit)
    nij_cf = np.maximum(0, -fz / f_compression_crit) + np.maximum(0, my / m_flexion_crit)
    nij_ce = np.maximum(0, -fz / f_compression_crit) + np.maximum(0, -my / m_extension_crit)

    modes = [
        ("Tension-Flexion", float(np.max(nij_tf))),
        ("Tension-Extension", float(np.max(nij_te))),
        ("Compression-Flexion", float(np.max(nij_cf))),
        ("Compression-Extension", float(np.max(nij_ce)))
    ]
    
    modes.sort(key=lambda x: x[1], reverse=True)
    worst_mode, worst_val = modes[0]
    
    return round(worst_val, 3), worst_mode

def compute_all_injury_metrics(timeseries_data: dict) -> dict:
    """Computes all required FAA/EASA AS8049E injury metrics from solver timeseries.
    
    STRICT NO-FALLBACK: If a signal channel is missing, returns None for that metric.
    """
    time_s = timeseries_data.get("time_s", [])
    head_accel = timeseries_data.get("head_acceleration", [])
    neck_my = timeseries_data.get("neck_moment", [])
    neck_fz = timeseries_data.get("neck_axial_force", [])
    femur_l = timeseries_data.get("femur_load_left", [])
    femur_r = timeseries_data.get("femur_load_right", [])
    lumbar = timeseries_data.get("lumbar_load", [])
    
    hic15_val = calculate_hic15(time_s, head_accel) if len(head_accel) > 0 else None
    nij_val, nij_type = calculate_nij(neck_fz, neck_my) if (len(neck_my) > 0 and len(neck_fz) > 0) else (None, None)

    femur_l_peak = float(round(np.max(np.abs(femur_l)), 2)) if len(femur_l) > 0 else None
    femur_r_peak = float(round(np.max(np.abs(femur_r)), 2)) if len(femur_r) > 0 else None
    lumbar_peak = float(round(np.max(np.abs(lumbar)), 2)) if len(lumbar) > 0 else None
    
    head_excursion = float(timeseries_data.get("head_excursion_mm")) if "head_excursion_mm" in timeseries_data else None
    knee_excursion = float(timeseries_data.get("knee_excursion_mm")) if "knee_excursion_mm" in timeseries_data else None
    seat_status = timeseries_data.get("seat_structural_status", "UNKNOWN")

    return {
        "hic15": hic15_val,
        "nij_max": nij_val,
        "nij_type": nij_type,
        "femur_load_left": femur_l_peak,
        "femur_load_right": femur_r_peak,
        "lumbar_load": lumbar_peak,
        "head_excursion_mm": head_excursion,
        "knee_excursion_mm": knee_excursion,
        "seat_structural_status": seat_status,
        "raw_timeseries": timeseries_data
    }
