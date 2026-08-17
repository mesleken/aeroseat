import numpy as np

# NHTSA / FAA 14 CFR § 25.562 Critical Injury Intercepts per Dummy Size
NIJ_CRITICAL_INTERCEPTS = {
    "FAA_HIII_50M": {
        "f_tens": 6811.0,    # N (1531 lbf)
        "f_comp": 6160.0,    # N (1385 lbf)
        "m_flex": 310.0,     # N*m (229 ft*lbf)
        "m_ext": 135.0       # N*m (100 ft*lbf)
    },
    "FAA_HIII_5F": {
        "f_tens": 4287.0,    # N (964 lbf)
        "f_comp": 3880.0,    # N (872 lbf)
        "m_flex": 155.0,     # N*m (114 ft*lbf)
        "m_ext": 67.0        # N*m (49 ft*lbf)
    },
    "FAA_HIII_95M": {
        "f_tens": 8216.0,    # N (1847 lbf)
        "f_comp": 7430.0,    # N (1670 lbf)
        "m_flex": 415.0,     # N*m (306 ft*lbf)
        "m_ext": 179.0       # N*m (132 ft*lbf)
    }
}

def apply_oc_moment_correction(
    my_cell: np.ndarray | list[float],
    fx_shear: np.ndarray | list[float],
    d_oc_m: float = 0.01778
) -> np.ndarray:
    """
    Applies SAE J211 / FAA AC 20-146A Occipital Condyle (OC) Moment Transformation.
    M_y_OC = M_y_cell - d_oc * F_x
    where d_oc = 0.01778 m (0.70 in) shear moment arm from loadcell center to OC joint.
    """
    my = np.asarray(my_cell, dtype=np.float64)
    fx = np.asarray(fx_shear, dtype=np.float64)
    return my - d_oc_m * fx

def calculate_hic15_with_window(time_s: np.ndarray | list[float], accel_g: np.ndarray | list[float]) -> tuple[float | None, float | None, float | None]:
    """Calculates HIC15 and returns (max_hic, t1_ms, t2_ms).
    
    HIC15 = max( (t2 - t1) * [ (1/(t2-t1)) * int_t1^t2 a(t) dt ]^2.5 )
    subject to (t2 - t1) <= 0.015 s.
    """
    t = np.asarray(time_s, dtype=np.float64)
    a = np.asarray(accel_g, dtype=np.float64)
    
    n = len(t)
    if n < 10 or np.all(a == 0):
        return None, None, None
    
    dt = np.mean(np.diff(t))
    if dt <= 0:
        return None, None, None
    
    cum_a = np.zeros(n, dtype=np.float64)
    for k in range(1, n):
        cum_a[k] = cum_a[k-1] + 0.5 * (a[k] + a[k-1]) * (t[k] - t[k-1])
    
    max_hic = 0.0
    best_t1 = 0.0
    best_t2 = 0.0
    max_samples_15ms = int(round(0.015 / dt)) + 1
    
    for i in range(n):
        for j in range(i + 1, min(i + max_samples_15ms + 1, n)):
            delta_t = t[j] - t[i]
            if delta_t <= 0.0 or delta_t > 0.015001:
                continue
            
            avg_a = (cum_a[j] - cum_a[i]) / delta_t
            if avg_a <= 0:
                continue
                
            hic_val = (avg_a ** 2.5) * delta_t
            if hic_val > max_hic:
                max_hic = hic_val
                best_t1 = t[i]
                best_t2 = t[j]

    if max_hic == 0.0:
        return 0.0, 0.0, 0.0

    return float(round(max_hic, 1)), float(round(best_t1 * 1000.0, 1)), float(round(best_t2 * 1000.0, 1))

def calculate_hic15(time_s: np.ndarray | list[float], accel_g: np.ndarray | list[float]) -> float | None:
    """Convenience wrapper for HIC15."""
    hic, _, _ = calculate_hic15_with_window(time_s, accel_g)
    return hic

def calculate_nij(
    fz_n: np.ndarray | list[float],
    my_nm: np.ndarray | list[float],
    dummy_type: str = "FAA_HIII_50M",
    fx_shear_n: np.ndarray | list[float] | None = None
) -> tuple[float | None, str | None]:
    """Calculates Nij for FAA Hybrid III Dummies across 4 neck injury modes per 14 CFR § 25.562."""
    fz = np.asarray(fz_n, dtype=np.float64)
    my = np.asarray(my_nm, dtype=np.float64)
    
    if len(fz) == 0 or len(my) == 0:
        return None, None

    # Apply OC moment correction if shear force is provided
    if fx_shear_n is not None and len(fx_shear_n) == len(my):
        my = apply_oc_moment_correction(my, fx_shear_n)

    intercepts = NIJ_CRITICAL_INTERCEPTS.get(dummy_type.upper(), NIJ_CRITICAL_INTERCEPTS["FAA_HIII_50M"])
    f_tension_crit = intercepts["f_tens"]
    f_compression_crit = intercepts["f_comp"]
    m_flexion_crit = intercepts["m_flex"]
    m_extension_crit = intercepts["m_ext"]

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
    """Computes all required FAA/EASA AS8049E injury metrics from solver timeseries."""
    time_s = timeseries_data.get("time_s", [])
    head_accel = timeseries_data.get("head_acceleration", [])
    neck_my = timeseries_data.get("neck_moment", [])
    neck_fz = timeseries_data.get("neck_axial_force", [])
    femur_l = timeseries_data.get("femur_load_left", [])
    femur_r = timeseries_data.get("femur_load_right", [])
    lumbar = timeseries_data.get("lumbar_load", [])
    belt_shoulder = timeseries_data.get("belt_shoulder_load_kn", [])
    belt_lap = timeseries_data.get("belt_lap_load_kn", [])
    dummy_type = timeseries_data.get("dummy_type", "FAA_HIII_50M")
    
    hic15_val, hic_t1, hic_t2 = calculate_hic15_with_window(time_s, head_accel) if len(head_accel) > 0 else (None, None, None)
    nij_val, nij_type = calculate_nij(neck_fz, neck_my, dummy_type=dummy_type) if (len(neck_my) > 0 and len(neck_fz) > 0) else (None, None)

    femur_l_peak = float(round(np.max(np.abs(femur_l)), 2)) if len(femur_l) > 0 else None
    femur_r_peak = float(round(np.max(np.abs(femur_r)), 2)) if len(femur_r) > 0 else None
    lumbar_peak = float(round(np.max(np.abs(lumbar)), 2)) if len(lumbar) > 0 else None
    belt_shoulder_peak = float(round(np.max(np.abs(belt_shoulder)), 2)) if len(belt_shoulder) > 0 else None
    belt_lap_peak = float(round(np.max(np.abs(belt_lap)), 2)) if len(belt_lap) > 0 else None
    
    head_excursion = float(timeseries_data.get("head_excursion_mm")) if "head_excursion_mm" in timeseries_data else None
    knee_excursion = float(timeseries_data.get("knee_excursion_mm")) if "knee_excursion_mm" in timeseries_data else None
    seat_status = timeseries_data.get("seat_structural_status", "INTACT_NO_FAILURE")

    return {
        "hic15": hic15_val,
        "hic15_t1_ms": hic_t1,
        "hic15_t2_ms": hic_t2,
        "nij_max": nij_val,
        "nij_type": nij_type,
        "femur_load_left": femur_l_peak,
        "femur_load_right": femur_r_peak,
        "lumbar_load": lumbar_peak,
        "belt_shoulder_load_kn": belt_shoulder_peak,
        "belt_lap_load_kn": belt_lap_peak,
        "head_excursion_mm": head_excursion,
        "knee_excursion_mm": knee_excursion,
        "seat_structural_status": seat_status,
        "delta_v_ms": timeseries_data.get("delta_v_ms", 14.1),
        "raw_timeseries": timeseries_data
    }
