import pytest
import numpy as np
from app.domain.physics.multibody.rigid_body import RigidBody6DOF
from app.domain.physics.multibody.articulated_joints import CervicalJoint, LumbarJoint
from app.domain.physics.multibody.energy_audit import EnergyMomentumAuditEngine

def test_rigid_body_6dof_newton_euler_integration():
    """Verifies Newton-Euler 6-DOF rigid body linear and rotational integration."""
    head = RigidBody6DOF(
        name="Head_Segment",
        mass_kg=4.54,
        inertia_kgm2=(0.022, 0.024, 0.020)
    )
    
    force_net = np.array([454.0, 0.0, 0.0]) # 10g acceleration along X
    moment_net = np.array([0.0, 4.54, 0.0])  # 4.54 Nm pitch moment
    
    dt = 0.001
    head.integrate_rk4_step(force_net, moment_net, dt=dt)
    
    assert abs(head.accel[0] - 100.0) < 1e-4 # a_x = 454 / 4.54 = 100.0 m/s^2
    assert head.pos[0] > 0.0
    assert head.omega[1] > 0.0
    assert head.compute_kinetic_energy() > 0.0

def test_articulated_cervical_and_lumbar_joints():
    """Verifies non-linear cervical and lumbar joint restoring torques and ROM limits."""
    cervical = CervicalJoint()
    lumbar = LumbarJoint()
    
    # Cervical flexion within ROM (+0.20 rad ~ +11 deg)
    t_cerv1, d_cerv1 = cervical.evaluate_restoring_torque(relative_angle_rad=0.20, relative_omega_rad_per_s=1.0)
    assert t_cerv1 > 0.0
    
    # Cervical extension beyond ROM limit (-0.45 rad < -0.35 rad limit) -> Progressive hardening boost
    t_cerv2, d_cerv2 = cervical.evaluate_restoring_torque(relative_angle_rad=-0.45, relative_omega_rad_per_s=-2.0)
    assert t_cerv2 < -10.0 # High restoring torque pulling head forward
    
    # Lumbar flexion torque
    t_lumb, d_lumb = lumbar.evaluate_restoring_torque(relative_angle_rad=0.30, relative_omega_rad_per_s=0.5)
    assert t_lumb > 0.0

def test_energy_momentum_audit_engine():
    """Verifies instantaneous energy & momentum conservation audit calculation."""
    audit = EnergyMomentumAuditEngine(initial_kinetic_energy_j=100.0)
    
    # Accumulate dissipation over time steps
    audit.update_dissipation(contact_diss_w=50.0, belt_diss_w=100.0, joint_diss_w=20.0, dt=0.1)
    
    # Current state: 75 J kinetic, 8 J potential
    res = audit.evaluate_audit(current_kinetic_energy_j=75.0, current_potential_energy_j=8.0)
    
    assert "energy_residual_ratio" in res
    assert "total_dissipated_energy_j" in res
    assert res["total_dissipated_energy_j"] == 17.0 # (50+100+20)*0.1 = 17 J
