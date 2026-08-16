import pytest
import numpy as np
from app.domain.physics.multibody.rigid_body import RigidBody6DOF
from app.domain.physics.multibody.energy_audit import EnergyMomentumAuditEngine

def test_conservation_matrix_a_free_rigid_body():
    """Test A: Free Rigid Body (F = M = 0 -> v = const, omega = const)."""
    body = RigidBody6DOF("Free_Body", mass_kg=10.0, inertia_kgm2=(1.0, 1.0, 1.0))
    body.vel = np.array([5.0, -2.0, 1.0])
    body.omega = np.array([0.1, 0.2, -0.1])
    
    v_init = body.vel.copy()
    omega_init = body.omega.copy()
    
    body.integrate_rk4_step(np.zeros(3), np.zeros(3), dt=0.01)
    
    np.testing.assert_allclose(body.vel, v_init, atol=1e-6)
    np.testing.assert_allclose(body.omega, omega_init, atol=1e-6)

def test_conservation_matrix_b_constant_force():
    """Test B: Constant Force (F = const -> a = F/m)."""
    body = RigidBody6DOF("Body_B", mass_kg=5.0, inertia_kgm2=(0.5, 0.5, 0.5))
    force = np.array([25.0, 0.0, 0.0]) # a = 5.0 m/s^2
    
    body.integrate_rk4_step(force, np.zeros(3), dt=0.1)
    
    assert abs(body.accel[0] - 5.0) < 1e-5
    assert abs(body.vel[0] - 0.50) < 1e-5

def test_conservation_matrix_c_constant_torque():
    """Test C: Constant Torque (M = const -> alpha = I^-1 * M)."""
    body = RigidBody6DOF("Body_C", mass_kg=2.0, inertia_kgm2=(0.2, 0.4, 0.5))
    moment = np.array([0.0, 2.0, 0.0]) # alpha_y = 2.0 / 0.4 = 5.0 rad/s^2
    
    body.integrate_rk4_step(np.zeros(3), moment, dt=0.1)
    
    assert abs(body.alpha[1] - 5.0) < 1e-5
    assert abs(body.omega[1] - 0.50) < 1e-5

def test_conservation_matrix_d_two_body_momentum():
    """Test D: Two-body Linear Momentum Conservation (sum m_i * v_i = const)."""
    b1 = RigidBody6DOF("Body1", mass_kg=4.0, inertia_kgm2=(1.0, 1.0, 1.0))
    b2 = RigidBody6DOF("Body2", mass_kg=6.0, inertia_kgm2=(1.0, 1.0, 1.0))
    
    b1.vel = np.array([10.0, 0.0, 0.0])
    b2.vel = np.array([0.0, 0.0, 0.0])
    
    p_initial = b1.mass * b1.vel + b2.mass * b2.vel
    
    # Internal action-reaction force pair F_12 = -F_21 = 100 N
    f1 = np.array([-100.0, 0.0, 0.0])
    f2 = np.array([100.0, 0.0, 0.0])
    
    dt = 0.01
    b1.integrate_rk4_step(f1, np.zeros(3), dt=dt)
    b2.integrate_rk4_step(f2, np.zeros(3), dt=dt)
    
    p_final = b1.mass * b1.vel + b2.mass * b2.vel
    np.testing.assert_allclose(p_final, p_initial, atol=1e-6)

def test_conservation_matrix_e_angular_momentum():
    """Test E: Angular Momentum Conservation (L = I * omega = const when M_ext = 0)."""
    body = RigidBody6DOF("Spinning_Body", mass_kg=3.0, inertia_kgm2=(0.1, 0.2, 0.3))
    body.omega = np.array([0.0, 0.0, 4.0]) # Spin around Z-axis
    
    L_initial = body.inertia_matrix @ body.omega
    
    body.integrate_rk4_step(np.zeros(3), np.zeros(3), dt=0.01)
    
    L_final = body.inertia_matrix @ body.omega
    np.testing.assert_allclose(L_final, L_initial, atol=1e-6)

def test_conservation_matrix_f_conservative_energy():
    """Test F: Conservative System Total Energy Conservation (E_total(t2) = E_total(t1))."""
    body = RigidBody6DOF("Energy_Body", mass_kg=2.0, inertia_kgm2=(0.1, 0.1, 0.1))
    body.vel = np.array([3.0, 4.0, 0.0]) # KE = 0.5 * 2.0 * (9+16) = 25 J
    
    ke_initial = body.compute_kinetic_energy()
    assert abs(ke_initial - 25.0) < 1e-5
    
    body.integrate_rk4_step(np.zeros(3), np.zeros(3), dt=0.05)
    ke_final = body.compute_kinetic_energy()
    
    assert abs(ke_final - ke_initial) < 1e-5

def test_conservation_matrix_g_damped_system_dissipation():
    """Test G: Damped System Energy Dissipation (E(t2) < E(t1) and E_diss >= 0)."""
    audit = EnergyMomentumAuditEngine(initial_kinetic_energy_j=50.0)
    
    # Damping power = 20 W over dt = 0.1 s -> Dissipates 2.0 J
    audit.update_dissipation(contact_diss_w=10.0, belt_diss_w=10.0, joint_diss_w=0.0, dt=0.1)
    
    res = audit.evaluate_audit(current_kinetic_energy_j=48.0, current_potential_energy_j=0.0)
    
    assert res["total_dissipated_energy_j"] == 2.0
    assert res["energy_audit_verdict"] == "NUMERICAL_ENERGY_BALANCE_PASS"
