import numpy as np
from scipy.interpolate import interp1d

def compute_euler_rotation_matrix(yaw_deg: float = 0.0, pitch_deg: float = 0.0, roll_deg: float = 0.0) -> np.ndarray:
    """Computes ZYX Tait-Bryan 3D rotation matrix for (yaw, pitch, roll) in degrees.
    
    yaw (psi): rotation around Z axis (vertical axis)
    pitch (theta): rotation around Y axis (lateral axis)
    roll (phi): rotation around X axis (longitudinal axis)
    """
    psi = np.radians(yaw_deg)
    theta = np.radians(pitch_deg)
    phi = np.radians(roll_deg)

    # Rotation around X (Roll)
    Rx = np.array([
        [1.0, 0.0, 0.0],
        [0.0, np.cos(phi), -np.sin(phi)],
        [0.0, np.sin(phi), np.cos(phi)]
    ], dtype=np.float64)

    # Rotation around Y (Pitch)
    Ry = np.array([
        [np.cos(theta), 0.0, np.sin(theta)],
        [0.0, 1.0, 0.0],
        [-np.sin(theta), 0.0, np.cos(theta)]
    ], dtype=np.float64)

    # Rotation around Z (Yaw)
    Rz = np.array([
        [np.cos(psi), -np.sin(psi), 0.0],
        [np.sin(psi), np.cos(psi), 0.0],
        [0.0, 0.0, 1.0]
    ], dtype=np.float64)

    # Combined rotation matrix: R = Rz * Ry * Rx
    return Rz @ Ry @ Rx

def generate_sae_16g_forward_pulse(t_array: np.ndarray, peak_g: float = 16.0) -> np.ndarray:
    """Generates standard 16g forward deceleration pulse per 14 CFR § 25.562 / SAE AS8049E.
    
    Standard specifies a triangular pulse with rise time <= 0.090s, total duration ~0.180s.
    Returns 1D array of acceleration magnitude in g.
    """
    pulse = np.zeros_like(t_array, dtype=np.float64)
    for i, t in enumerate(t_array):
        if t < 0.0:
            pulse[i] = 0.0
        elif t <= 0.090:
            # Rise phase: 0 -> peak_g
            pulse[i] = peak_g * (t / 0.090)
        elif t <= 0.180:
            # Decay phase: peak_g -> 0
            pulse[i] = peak_g * (1.0 - (t - 0.090) / 0.090)
        else:
            pulse[i] = 0.0
    return pulse

def generate_sae_14g_downward_pulse(t_array: np.ndarray, peak_g: float = 14.0) -> np.ndarray:
    """Generates standard 14g downward deceleration pulse per 14 CFR § 25.562 / SAE AS8049E.
    
    Standard specifies a triangular pulse peaking at 14g with rise time <= 0.080s, duration ~0.160s.
    Returns 1D array of acceleration magnitude in g.
    """
    pulse = np.zeros_like(t_array, dtype=np.float64)
    for i, t in enumerate(t_array):
        if t < 0.0:
            pulse[i] = 0.0
        elif t <= 0.080:
            pulse[i] = peak_g * (t / 0.080)
        elif t <= 0.160:
            pulse[i] = peak_g * (1.0 - (t - 0.080) / 0.080)
        else:
            pulse[i] = 0.0
    return pulse

def interpolate_custom_pulse(
    t_model: np.ndarray,
    custom_time: list[float] | np.ndarray,
    custom_accel: list[float] | np.ndarray
) -> np.ndarray:
    """Interpolates user-uploaded pulse data to model simulation time grid."""
    t_c = np.asarray(custom_time, dtype=np.float64)
    a_c = np.asarray(custom_accel, dtype=np.float64)
    if len(t_c) < 2 or len(a_c) < 2:
        return np.zeros_like(t_model)

    interp_fn = interp1d(t_c, a_c, kind="linear", bounds_error=False, fill_value=0.0)
    return interp_fn(t_model)

def transform_pulse_3d(
    t_array: np.ndarray,
    pulse_type: str = "FORWARD_16G",
    yaw_deg: float = 0.0,
    pitch_deg: float = 0.0,
    roll_deg: float = 0.0,
    custom_pulse_data: dict | None = None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generates and rotates 3D acceleration pulse vector [ax(t), ay(t), az(t)] (in m/s^2).
    
    Coordinate convention (SAE J211 Occupant Axis System):
    - X: Forward (+X forward)
    - Y: Right (+Y right)
    - Z: Downward (+Z down)
    
    Returns (ax_m_s2, ay_m_s2, az_m_s2).
    """
    g_to_ms2 = 9.80665
    
    if custom_pulse_data and "time_s" in custom_pulse_data and "acceleration_g" in custom_pulse_data:
        mag_g = interpolate_custom_pulse(
            t_array,
            custom_pulse_data["time_s"],
            custom_pulse_data["acceleration_g"]
        )
        if "14G" in pulse_type.upper() or "DOWN" in pulse_type.upper() or "VERT" in pulse_type.upper():
            base_vector = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        else:
            base_vector = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    elif "14G" in pulse_type.upper() or "DOWN" in pulse_type.upper() or "VERT" in pulse_type.upper():
        mag_g = generate_sae_14g_downward_pulse(t_array, peak_g=14.0)
        # 14g base vector is purely in +Z direction (downward compression)
        base_vector = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    else:
        mag_g = generate_sae_16g_forward_pulse(t_array, peak_g=16.0)
        # 16g base vector is in +X direction (forward deceleration)
        base_vector = np.array([1.0, 0.0, 0.0], dtype=np.float64)

    # Compute rotation matrix
    R = compute_euler_rotation_matrix(yaw_deg, pitch_deg, roll_deg)
    rotated_dir = R @ base_vector

    # Multiply magnitude across time
    ax = mag_g * rotated_dir[0] * g_to_ms2
    ay = mag_g * rotated_dir[1] * g_to_ms2
    az = mag_g * rotated_dir[2] * g_to_ms2

    return ax, ay, az
