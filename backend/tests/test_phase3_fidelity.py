import pytest
import numpy as np
from app.domain.physics.multibody.rigid_body import RigidBody6DOF
from app.domain.physics.multibody.momentum_audit import MomentumAuditEngine
from app.domain.physics.multibody.constraint_audit import ConstraintAuditEngine
from app.domain.physics.multibody.restraint_state_machine import RestraintSubsystemStateMachine
from app.domain.physics.multibody.evidence_vector import EvidenceConfidenceVectorEngine

def test_momentum_audit_engine():
    """Verifies linear and angular momentum audit calculations and verdict."""
    b1 = RigidBody6DOF("Head", mass_kg=4.54, inertia_kgm2=(0.02, 0.02, 0.02))
    b1.vel = np.array([10.0, 0.0, 0.0])
    
    audit = MomentumAuditEngine(rigid_bodies=[b1])
    res = audit.evaluate_audit(f_ext_sum_n=np.zeros(3), dt=0.01)
    
    assert res["linear_momentum_norm_kgm_per_s"] == 45.4 # 4.54 * 10.0
    assert res["momentum_audit_verdict"] == "NUMERICAL_MOMENTUM_BALANCE_PASS"

def test_constraint_audit_engine():
    """Verifies kinematic constraint drift and velocity error audits."""
    audit = ConstraintAuditEngine(position_tolerance_m=1e-3, velocity_tolerance_m_per_s=1e-2)
    
    C_res = np.array([1e-5, 2e-5]) # 0.01 mm drift
    J = np.array([[1.0, 0.0], [0.0, 1.0]])
    q_dot = np.array([1e-4, 1e-4])
    
    res = audit.evaluate_constraint_audit(C_res, J, q_dot)
    
    assert res["constraint_audit_verdict"] == "NUMERICAL_CONSTRAINT_PASS"
    assert res["max_position_constraint_drift_m"] < 1e-3

def test_restraint_subsystem_state_machine():
    """Verifies restraint state machine transitions and load limiter absorbed energy."""
    fsm = RestraintSubsystemStateMachine(slack_m=0.015, load_limit_n=6000.0)
    
    # State 1: SLACK (extension <= 0)
    state1 = fsm.update_state(current_extension_m=0.0, extension_vel_m_per_s=0.0, tension_n=0.0, dt=0.01)
    assert state1 == "SLACK"
    
    # State 2: LOAD_LIMITING (tension >= 6000 N)
    state2 = fsm.update_state(current_extension_m=0.050, extension_vel_m_per_s=0.5, tension_n=6000.0, dt=0.01)
    assert state2 == "LOAD_LIMITING"
    
    audit = fsm.get_audit()
    assert audit["absorbed_load_limiter_energy_j"] > 0.0 # 6000 N * 0.5 m/s * 0.01 s = 30 J

def test_evidence_confidence_vector_engine():
    """Verifies multi-dimensional evidence confidence vector generation."""
    vector = EvidenceConfidenceVectorEngine.generate_confidence_vector(
        numerical_verification_passed=True,
        constraint_audit_verdict="NUMERICAL_CONSTRAINT_PASS",
        energy_audit_verdict="NUMERICAL_ENERGY_BALANCE_PASS",
        experimental_validation_dataset=False
    )
    
    ev = vector["evidence_confidence_vector"]
    assert ev["constraint_verification"] == "NUMERICAL_CONSTRAINT_PASS"
    assert ev["biomechanical_validation"] == "NOT_YET_VALIDATED"
    assert ev["overall_certification_readiness"] == "VERIFICATION_BASELINE_ESTABLISHED_VALIDATION_PENDING"
