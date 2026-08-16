import pytest
import numpy as np
from app.domain.physics.restraint_system import RestraintSystem
from app.domain.physics.contact_mechanics import HuntCrossleyContact
from app.domain.physics.uncertainty_engine import UncertaintyQuantificationEngine
from app.domain.physics.calibration_engine import ModelCalibrationEngine

def test_restraint_system_3d_line_of_action_and_load_limiter():
    """Verifies 3D line-of-action belt force vector, pretensioner stroke, and load limiter capping."""
    restraint = RestraintSystem(
        stiffness_n_per_m=150000.0,
        pretensioner_active=True,
        pretensioner_fire_ms=10.0,
        load_limiter_active=True,
        load_limiter_threshold_n=6000.0
    )
    
    anchor = np.array([0.50, 0.20, 0.80])
    node = np.array([0.10, 0.0, 0.40])
    node_vel = np.array([-2.0, 0.0, 0.0]) # Moving away from anchor
    
    # Test 1: Fire pretensioner at t = 0.020 s (20 ms)
    tension, force_vec, extension = restraint.evaluate_belt_tension(
        anchor_pos=anchor,
        node_pos=node,
        node_vel=node_vel,
        initial_length_m=0.55,
        time_s=0.020
    )
    
    assert tension > 0.0
    assert tension <= 6000.0 # Capped by load limiter
    assert len(force_vec) == 3
    # Direction check: Force points from node toward anchor
    e_expected = (anchor - node) / np.linalg.norm(anchor - node)
    np.testing.assert_allclose(force_vec / tension, e_expected, atol=1e-5)

def test_hunt_crossley_contact_mechanics():
    """Verifies Hunt-Crossley non-linear unilateral contact mechanics and bottoming-out stiffness."""
    contact = HuntCrossleyContact(
        stiffness_k=85000.0,
        exponent_n=1.5,
        bottoming_penetration_m=0.030
    )
    
    # Test 1: Penetration delta = 0.010 m (normal range)
    fn1, ff1 = contact.evaluate_normal_force(penetration_m=0.010, penetration_velocity_m_per_s=0.5)
    assert fn1 > 0.0
    
    # Test 2: Penetration delta = 0.040 m (bottoming-out range) -> Fn increases non-linearly
    fn2, ff2 = contact.evaluate_normal_force(penetration_m=0.040, penetration_velocity_m_per_s=0.5)
    assert fn2 > fn1 * 5.0 # Non-linear bottoming-out stiffness boost
    
    # Test 3: Unilateral constraint (disengagement delta <= 0 -> Fn = 0)
    fn3, ff3 = contact.evaluate_normal_force(penetration_m=-0.005, penetration_velocity_m_per_s=-1.0)
    assert fn3 == 0.0 and ff3 == 0.0

def test_uncertainty_quantification_engine():
    """Verifies Monte Carlo sampling 95% confidence intervals and sensitivity analysis."""
    uq = UncertaintyQuantificationEngine(seed=42)
    res = uq.run_monte_carlo(n_samples=5, tolerance_pct=10.0)
    
    assert res["n_samples"] == 5
    assert "hic15" in res
    assert res["hic15"]["ci95_high"] >= res["hic15"]["mean"]
    assert res["hic15"]["ci95_low"] <= res["hic15"]["mean"]
    assert len(res["sensitivity_rankings"]) > 0

def test_model_calibration_engine():
    """Verifies calibration loss evaluation and independent validation split."""
    calibrator = ModelCalibrationEngine()
    params = {"k_belt_scale": 1.05, "c_neck_scale": 0.95}
    eval_res = calibrator.evaluate_calibration_status(params)
    
    assert "calibration_loss_j" in eval_res
    assert "validation_loss_j" in eval_res
    assert "calibration_status" in eval_res
