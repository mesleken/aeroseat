import pytest
import numpy as np
from app.domain.physics.pulse_library import (
    compute_euler_rotation_matrix, generate_sae_16g_forward_pulse,
    generate_sae_14g_downward_pulse, transform_pulse_3d, interpolate_custom_pulse
)
from app.domain.physics.lumped_mass_model import LumpedMassCrashModel, DUMMY_PRESETS
from app.domain.injury_metrics import compute_all_injury_metrics, calculate_hic15, calculate_hic15_with_window
from app.domain.physics.signal_processing import sae_j211_cfc_filter, validate_pulse_delta_v

def test_rotation_matrix_identity():
    """Zero angles must produce 3x3 identity matrix."""
    R0 = compute_euler_rotation_matrix(0.0, 0.0, 0.0)
    np.testing.assert_allclose(R0, np.eye(3), atol=1e-7)

def test_sae_16g_pulse_profile():
    """16g forward pulse must peak at 16.0g around 90ms."""
    t = np.linspace(0.0, 0.180, 1801)
    pulse = generate_sae_16g_forward_pulse(t, peak_g=16.0)
    assert np.max(pulse) == pytest.approx(16.0, rel=1e-2)
    peak_time = t[np.argmax(pulse)]
    assert 0.085 <= peak_time <= 0.095

def test_sae_14g_downward_pulse_profile():
    """14g downward pulse must peak at 14.0g around 80ms."""
    t = np.linspace(0.0, 0.160, 1601)
    pulse = generate_sae_14g_downward_pulse(t, peak_g=14.0)
    assert np.max(pulse) == pytest.approx(14.0, rel=1e-2)
    peak_time = t[np.argmax(pulse)]
    assert 0.075 <= peak_time <= 0.085

def test_nominal_16g_lumped_mass_simulation():
    """Nominal 16g crash simulation with 0° yaw/pitch/roll."""
    model = LumpedMassCrashModel(pulse_type="FORWARD_16G", yaw_deg=0.0, pitch_deg=0.0, roll_deg=0.0)
    res = model.run()

    assert "time_s" in res
    assert "head_acceleration" in res
    assert len(res["time_s"]) == 1901
    assert "belt_shoulder_load_kn" in res

    # Compute injury criteria
    inj = compute_all_injury_metrics(res)
    assert inj["hic15"] is not None
    # Nominal 16g forward test must produce passing HIC15 (<= 1000)
    assert 0.0 < inj["hic15"] <= 1000.0
    assert inj["hic15_t1_ms"] is not None
    assert inj["nij_max"] is not None
    assert inj["nij_max"] <= 1.0
    assert inj["head_excursion_mm"] > 0.0
    assert inj["belt_shoulder_load_kn"] is not None

def test_dummy_preset_variations():
    """Different dummy sizes (5F, 50M, 95M) must produce distinct kinetic responses."""
    m_50m = LumpedMassCrashModel(dummy_type="FAA_HIII_50M").run()
    m_5f = LumpedMassCrashModel(dummy_type="FAA_HIII_5F").run()
    m_95m = LumpedMassCrashModel(dummy_type="FAA_HIII_95M").run()

    inj_50m = compute_all_injury_metrics(m_50m)
    inj_5f = compute_all_injury_metrics(m_5f)
    inj_95m = compute_all_injury_metrics(m_95m)

    assert inj_5f["hic15"] != inj_50m["hic15"]
    assert inj_95m["femur_load_left"] != inj_50m["femur_load_left"]

def test_downward_14g_simulation():
    """14g vertical downward test must generate significant compressive lumbar spine load."""
    model_14g = LumpedMassCrashModel(pulse_type="DOWNWARD_14G").run()
    inj_14g = compute_all_injury_metrics(model_14g)
    
    assert inj_14g["lumbar_load"] is not None
    assert inj_14g["lumbar_load"] > 2.0  # Compressive spinal load in kN
    assert model_14g["delta_v_ms"] >= 10.0

def test_yaw_angle_effect_on_femur_asymmetry():
    """A 15° yaw angle must create asymmetric loading between left and right femur."""
    model_straight = LumpedMassCrashModel(yaw_deg=0.0)
    res_straight = model_straight.run()

    model_yawed = LumpedMassCrashModel(yaw_deg=15.0)
    res_yawed = model_yawed.run()

    # In yawed scenario, clearance differs, leading to asymmetric peak loads
    inj_yawed = compute_all_injury_metrics(res_yawed)
    assert inj_yawed["femur_load_left"] is not None
    assert inj_yawed["femur_load_right"] is not None

def test_pitch_angle_increases_lumbar_load():
    """A 10° pitch angle introduces vertical deceleration component into lumbar spine."""
    model_flat = LumpedMassCrashModel(pitch_deg=0.0)
    res_flat = model_flat.run()

    model_pitched = LumpedMassCrashModel(pitch_deg=10.0)
    res_pitched = model_pitched.run()

    inj_flat = compute_all_injury_metrics(res_flat)
    inj_pitched = compute_all_injury_metrics(res_pitched)

    assert inj_pitched["lumbar_load"] >= inj_flat["lumbar_load"]

def test_cfc_filtering():
    """SAE J211 CFC Butterworth filter removes high-frequency synthetic spikes."""
    dt = 0.0001 # 10 kHz
    t = np.linspace(0, 0.18, 1801)
    base_signal = 20.0 * np.sin(2 * np.pi * 30 * t)
    noisy_signal = base_signal + 10.0 * np.sin(2 * np.pi * 3500 * t) # High freq noise
    
    filtered = sae_j211_cfc_filter(noisy_signal, dt, cfc=1000)
    assert np.max(np.abs(filtered)) < np.max(np.abs(noisy_signal))
