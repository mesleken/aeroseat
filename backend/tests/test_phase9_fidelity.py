import pytest
import numpy as np
from app.domain.physics.lumped_mass_model import LumpedMassCrashModel, RestraintAndStiffnessConfig
from app.domain.physics.multibody.constitutive import ConstitutiveModels
from app.domain.physics.seat.seat_structure import SeatStructureCompliance, SeatMountingCompliance
from app.domain.injury_metrics import calculate_hic15_with_window, calculate_nij, compute_all_injury_metrics

def test_phase9_001_cushion_3phase_foam_mechanics():
    """Verifies that the 3-phase open-cell foam cushion exhibits linear, plateau, and densification stages."""
    k = 48000.0
    c = 2200.0
    
    # Phase 1: Small penetration (Linear)
    f_p1 = ConstitutiveModels.cushion_3phase_foam(penetration_m=0.015, velocity_mps=1.0, k_cushion=k, c_cushion=c)
    # Phase 2: Plateau (0.025 to 0.065 m)
    f_p2 = ConstitutiveModels.cushion_3phase_foam(penetration_m=0.045, velocity_mps=1.0, k_cushion=k, c_cushion=c)
    # Phase 3: Densification / Bottom-out (> 0.065 m)
    f_p3 = ConstitutiveModels.cushion_3phase_foam(penetration_m=0.085, velocity_mps=1.0, k_cushion=k, c_cushion=c)
    
    assert f_p1 > 0.0
    assert f_p2 > f_p1
    assert f_p3 > f_p2 * 2.0  # Sharp densification stiffening
    
    # Hysteretic energy loss: Unloading force must be lower than loading force at same displacement
    f_loading = ConstitutiveModels.cushion_3phase_foam(penetration_m=0.040, velocity_mps=0.5, k_cushion=k, c_cushion=c)
    f_unloading = ConstitutiveModels.cushion_3phase_foam(penetration_m=0.040, velocity_mps=-0.5, k_cushion=k, c_cushion=c)
    assert f_unloading < f_loading

def test_phase9_002_persistent_seatback_plasticity():
    """Verifies that seatback retains permanent plastic set angle after severe moment loading and rebound."""
    engine = SeatStructureCompliance(
        seatback_rotational_k_nm_per_rad=32000.0,
        seatback_rotational_c_nms_per_rad=650.0,
        yield_torque_nm=1200.0,
        inertia_kg_m2=1.35
    )
    
    dt = 0.001
    # Apply severe crash moment exceeding yield torque (e.g. 2500 Nm for 50 ms)
    for _ in range(50):
        engine.evaluate_seatback_response(applied_moment_nm=2500.0, dt=dt)
        
    assert engine.is_yielded is True
    assert engine.plastic_angle_rad > 0.0
    
    # Remove load and allow rebound for 100 ms
    for _ in range(100):
        angle, m_rest = engine.evaluate_seatback_response(applied_moment_nm=0.0, dt=dt)
        
    # Persistent set: final angle must remain > 0 (permanent plastic set)
    assert engine.seatback_angle_rad > 0.02  # Retained permanent deformation

def test_phase9_003_dummy_specific_nij_intercepts():
    """Verifies that Nij evaluation scales properly with dummy size (50M, 5F, 95M)."""
    fz_test = np.array([3000.0, 3500.0, 4000.0])
    my_test = np.array([100.0, 120.0, 140.0])
    
    nij_50m, mode_50m = calculate_nij(fz_test, my_test, dummy_type="FAA_HIII_50M")
    nij_5f, mode_5f = calculate_nij(fz_test, my_test, dummy_type="FAA_HIII_5F")
    nij_95m, mode_95m = calculate_nij(fz_test, my_test, dummy_type="FAA_HIII_95M")
    
    assert nij_50m is not None
    assert nij_5f is not None
    assert nij_95m is not None
    
    # 5F female dummy has smaller tolerance, so same forces yield higher Nij index
    assert nij_5f > nij_50m
    # 95M male dummy has larger tolerance, so same forces yield lower Nij index
    assert nij_95m < nij_50m

def test_phase9_004_14g_downward_fidelity_and_femur_dynamics():
    """Verifies 14G downward simulation produces dynamic femur loads and realistic lumbar compression."""
    model = LumpedMassCrashModel(pulse_type="DOWNWARD_14G", dummy_type="FAA_HIII_50M")
    res = model.run()
    
    lumbar = np.array(res["lumbar_load"], dtype=np.float64)
    femur_l = np.array(res["femur_load_left"], dtype=np.float64)
    femur_r = np.array(res["femur_load_right"], dtype=np.float64)
    
    # Lumbar load in 14G must reach significant spinal compressive load within FAA corridor
    peak_lumbar = float(np.max(lumbar))
    assert 2.0 < peak_lumbar < 7.0  # Realistic 2 - 7 kN corridor
    
    # Femur loads in 14G must be dynamically computed (not flat hardcoded 0.40)
    assert not np.all(femur_l == 0.40)
    assert float(np.max(femur_l)) > 0.1
    assert float(np.max(femur_r)) > 0.1

def test_phase9_005_16g_forward_crashworthiness_corridors():
    """Verifies 16G forward simulation metrics fall within established NHTSA/CAMI test corridors."""
    model = LumpedMassCrashModel(pulse_type="FORWARD_16G", dummy_type="FAA_HIII_50M")
    res = model.run()
    
    head_accel = np.array(res["head_acceleration"], dtype=np.float64)
    shoulder_belt = np.array(res["belt_shoulder_load_kn"], dtype=np.float64)
    lap_belt = np.array(res["belt_lap_load_kn"], dtype=np.float64)
    
    peak_head_g = float(np.max(head_accel))
    peak_shoulder_kn = float(np.max(shoulder_belt))
    peak_lap_kn = float(np.max(lap_belt))
    
    # Real 16G Sled Test Corridors:
    # - Peak Head Accel: 25 - 65 g
    # - Peak Shoulder Belt: 3 - 9 kN
    # - Peak Lap Belt: 3 - 10 kN
    assert 25.0 <= peak_head_g <= 65.0
    assert 3.0 <= peak_shoulder_kn <= 10.0
    assert 3.0 <= peak_lap_kn <= 10.0
    
    # HIC15 Calculation
    metrics = compute_all_injury_metrics(res)
    hic15 = metrics["hic15"]
    assert hic15 is not None
    assert 20.0 <= hic15 <= 850.0
