import pytest
import numpy as np

from app.domain.physics.lumped_mass_model import LumpedMassCrashModel, RestraintAndStiffnessConfig
from app.domain.physics.multibody.constitutive import ConstitutiveModels
from app.domain.physics.multibody.articulated_joint import ArticulatedJoint, ArticulatedJointConfig
from app.domain.physics.multibody.contact_geometry import ObstacleContactEngine, FlailEnvelopeContactConfig, ObstacleSurface
from app.domain.injury_metrics import compute_all_injury_metrics

def test_phase12_001_ls_dyna_soft1_contact_stiffness():
    """Verifies LS-DYNA SOFT=1 mass/timestep-based contact stiffness scaling."""
    m_head = 4.54
    m_obs = 15.0
    dt_1 = 0.0001
    dt_2 = 0.00005 # Halved dt -> 4x stiffness
    
    k1 = ConstitutiveModels.compute_soft1_contact_stiffness(m_head, m_obs, dt_1, sofscl=0.10)
    k2 = ConstitutiveModels.compute_soft1_contact_stiffness(m_head, m_obs, dt_2, sofscl=0.10)
    
    assert k1 > 0.0
    assert abs(k2 / k1 - 4.0) < 1e-3 # Quad scaling with 1/dt^2

def test_phase12_002_openradioss_critical_timestep():
    """Verifies OpenRadioss Courant-Friedrichs-Lewy critical timestep calculation."""
    m_eff = 3.5
    k_eff = 50000.0
    tssfac = 0.70
    
    dt_crit = ConstitutiveModels.compute_critical_timestep(m_eff, k_eff, tssfac=tssfac)
    
    omega_n = np.sqrt(k_eff / m_eff)
    expected_dt = tssfac * (2.0 / omega_n)
    
    assert abs(dt_crit - expected_dt) < 1e-6
    assert 0.05 > dt_crit > 0.00001

def test_phase12_003_modular_articulated_joint_mechanics():
    """Verifies Simscape-inspired modular ArticulatedJoint restoring moments and anatomical limits."""
    cfg = ArticulatedJointConfig(
        name="TEST_KNEE",
        k_rot=4500.0,
        c_rot=120.0,
        limit_min_rad=-0.10,
        limit_max_rad=2.00,
        stop_k=85000.0,
        stop_c=2500.0
    )
    joint = ArticulatedJoint(cfg)
    
    # 1. Nominal flexion within limits (theta = 0.5 rad)
    m1, exceeded1 = joint.compute_restoring_moment(0.5, 0.0)
    assert not exceeded1
    assert m1 > 0.0
    
    # 2. Exceeding anatomical limit stop (theta = 2.2 rad > limit_max_rad=2.0)
    m2, exceeded2 = joint.compute_restoring_moment(2.2, 0.0)
    assert exceeded2
    assert m2 > m1 * 5.0 # Sharp anatomical limit stop reaction

def test_phase12_004_bounded_polygon_obstacle_contact():
    """Verifies that head contact only triggers inside the 2D obstacle bounding box."""
    cfg = FlailEnvelopeContactConfig(obstacles=[
        ObstacleSurface(
            position_m=(0.80, 0.0, -0.20),
            normal_vector=(-1.0, 0.0, 0.0),
            width_m=0.40,
            height_m=0.40,
            use_soft1_stiffness=True
        )
    ])
    engine = ObstacleContactEngine(cfg)
    
    # Position A: Center hit -> Contact
    fx_hit, _, _, pen_hit, is_hit = engine.evaluate_head_contact(
        head_cg_pos_m=(0.82, 0.0, -0.20),
        head_vel_mps=(10.0, 0.0, 0.0),
        head_mass_kg=4.54,
        dt_s=0.0001
    )
    assert is_hit
    assert fx_hit < 0.0 # Pushes back
    
    # Position B: Lateral miss (dy = 0.40 m > width/2 + radius) -> No contact
    fx_miss, _, _, _, is_miss = engine.evaluate_head_contact(
        head_cg_pos_m=(0.82, 0.45, -0.20),
        head_vel_mps=(10.0, 0.0, 0.0),
        head_mass_kg=4.54,
        dt_s=0.0001
    )
    assert not is_miss
    assert fx_miss == 0.0

def test_phase12_005_industrial_solver_full_run():
    """Verifies end-to-end crash simulation with Phase 12 industrial solvers."""
    model = LumpedMassCrashModel(pulse_type="FORWARD_16G", forward_obstacle_pitch_inches=32.0)
    res = model.run()
    metrics = compute_all_injury_metrics(res)
    
    assert res["delta_v_valid"] is True
    assert metrics["hic15"] is not None
    assert metrics["nij_max"] is not None
    assert metrics["lumbar_load"] is not None
    assert len(res["frames"]["head"]["acceleration_g"]) == len(res["time_s"])
