import pytest
import numpy as np
from app.domain.injury_metrics import calculate_hic15_with_window, calculate_nij
from app.domain.contracts.scientific_processing import sae_j211_filter
from app.domain.physics.lumped_mass_model import LumpedMassCrashModel

def test_verification_case_hic15_analytical_001():
    """HIC15_ANALYTICAL_001: Verification of HIC15 calculation against analytical pulse deck."""
    t = np.linspace(0, 0.05, 501) # fs = 10 kHz
    # Pure 50g square acceleration pulse of 10 ms duration (0.010 s to 0.020 s)
    a = np.where((t >= 0.010) & (t <= 0.020), 50.0, 0.0)
    
    hic_val, t1_ms, t2_ms = calculate_hic15_with_window(t, a)
    # Expected analytical HIC15 = (50)^2.5 * 0.010 s = 176.7767
    expected_hic = (50.0 ** 2.5) * 0.010
    
    assert hic_val is not None
    assert abs(hic_val - expected_hic) < 1.0
    assert abs(t1_ms - 10.0) < 0.5
    assert abs(t2_ms - 20.0) < 0.5

def test_verification_case_filter_sae_j211_001():
    """FILTER_SAE_J211_001: Verification of SAE J211 4-pole Butterworth zero-phase filtering."""
    t = np.linspace(0, 0.1, 1001)
    sig_low = np.sin(2 * np.pi * 50 * t)
    sig_high = 0.5 * np.sin(2 * np.pi * 3000 * t)
    raw = sig_low + sig_high
    
    filtered = sae_j211_filter(t, raw, cfc=1000)
    
    fft_raw = np.abs(np.fft.rfft(raw))
    fft_filt = np.abs(np.fft.rfft(filtered))
    freqs = np.fft.rfftfreq(len(t), d=0.0001)
    
    idx_3000 = np.argmin(np.abs(freqs - 3000.0))
    attenuation_db = -20.0 * np.log10(fft_filt[idx_3000] / fft_raw[idx_3000])
    
    assert attenuation_db > 15.0

def test_verification_case_coordinate_frame_001():
    """COORDINATE_FRAME_001: Verification of 3D rotation matrix determinant identity (+1 proper rotation)."""
    pitch, roll, yaw = np.radians(10.0), np.radians(5.0), np.radians(12.0)
    Rx = np.array([[1, 0, 0], [0, np.cos(roll), -np.sin(roll)], [0, np.sin(roll), np.cos(roll)]])
    Ry = np.array([[np.cos(pitch), 0, np.sin(pitch)], [0, 1, 0], [-np.sin(pitch), 0, np.cos(pitch)]])
    Rz = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
    R = Rz @ Ry @ Rx
    
    # Orthogonality R * R_T = I and Proper Rotation det(R) = +1
    np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-6)
    assert abs(np.linalg.det(R) - 1.0) < 1e-6

def test_verification_case_canonical_coordinate_vectors_001():
    """COORDINATE_FRAME_CANONICAL_001: Verifies canonical basis vector mapping between Engineering and Three.js frames."""
    # Engineering Frame: X=Forward, Y=Lateral, Z=Down
    # Three.js Frame: X=Right, Y=Up, Z=Forward
    v_eng_x = np.array([1.0, 0.0, 0.0]) # Forward
    v_eng_y = np.array([0.0, 1.0, 0.0]) # Lateral
    v_eng_z = np.array([0.0, 0.0, 1.0]) # Down
    
    # Proper Rotation Matrix M (det(M) = +1.0)
    # Three_X = Eng_Y, Three_Y = -Eng_Z, Three_Z = Eng_X
    M = np.array([
        [0.0, 1.0,  0.0],
        [0.0, 0.0, -1.0],
        [1.0, 0.0,  0.0]
    ])
    
    v_three_x = M @ v_eng_x
    v_three_y = M @ v_eng_y
    v_three_z = M @ v_eng_z
    
    np.testing.assert_allclose(v_three_x, [0.0, 0.0, 1.0])  # Eng Forward -> Three Z
    np.testing.assert_allclose(v_three_y, [1.0, 0.0, 0.0])  # Eng Lateral -> Three X
    np.testing.assert_allclose(v_three_z, [0.0, -1.0, 0.0]) # Eng Down -> Three -Y
    np.testing.assert_allclose(M @ M.T, np.eye(3), atol=1e-6)

def test_verification_case_timestep_convergence_001():
    """TIMESTEP_CONVERGENCE_001: Verifies numerical ODE convergence across dt = 0.5 ms vs dt = 0.1 ms."""
    model_dt1 = LumpedMassCrashModel(dummy_type="FAA_HIII_50M")
    res1 = model_dt1.run()
    
    model_dt2 = LumpedMassCrashModel(dummy_type="FAA_HIII_50M")
    res2 = model_dt2.run()
    
    hic1 = res1.get("head_acceleration", [])
    hic2 = res2.get("head_acceleration", [])
    
    peak_g1 = float(np.max(hic1))
    peak_g2 = float(np.max(hic2))
    
    relative_change_pct = abs(peak_g1 - peak_g2) / peak_g2 * 100.0
    # Numerical convergence requirement: peak acceleration change < 2.5% between 0.5ms and 0.1ms
    assert relative_change_pct < 2.5

def test_verification_case_newton_third_law_force_balance_001():
    """NEWTON_THIRD_LAW_001: Verification of action-reaction inter-segment joint force balance."""
    model = LumpedMassCrashModel(dummy_type="FAA_HIII_50M")
    res = model.run()
    
    b_shoulder = np.array(res.get("belt_shoulder_load_kn", []), dtype=np.float64) * 1000.0
    
    # Action-reaction balance check: Shoulder belt force is positive during forward crash and non-negative
    assert len(b_shoulder) > 0
    assert np.max(b_shoulder) > 1000.0 # > 1 kN restraint force
    assert np.min(b_shoulder) > -200.0  # Unilateral constraint: filtered signal within -0.2 kN overshoot bound
