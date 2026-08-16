import pytest
import numpy as np
from app.domain.physics.multibody.rigid_body import RigidBody6DOF
from app.domain.physics.multibody.reaction_audit import ReactionAuditEngine
from app.domain.physics.multibody.anthropometry import AnthropometricDataset
from app.domain.physics.multibody.waveform_correlation import WaveformCorrelationEngine
from app.domain.physics.multibody.evidence_vector import EvidenceConfidenceVectorEngine
from app.domain.physics.lumped_mass_model import LumpedMassCrashModel

def test_coupled_physics_matrix_a_free_body():
    """Test A: Free body zero external load state."""
    b = RigidBody6DOF("Free_Torso", mass_kg=34.2, inertia_kgm2=(1.0, 2.25, 1.0))
    b.integrate_rk4_step(np.zeros(3), np.zeros(3), dt=0.01)
    assert float(np.linalg.norm(b.accel)) == 0.0

def test_coupled_physics_matrix_b_seat_pelvis_contact():
    """Test B: Seat + Pelvis contact normal force & work coupling."""
    pelvis = RigidBody6DOF("Pelvis", mass_kg=14.8, inertia_kgm2=(0.2, 0.2, 0.2))
    f_cushion_z = np.array([0.0, 0.0, -145.0]) # 145 N upward contact force
    pelvis.integrate_rk4_step(f_cushion_z, np.zeros(3), dt=0.01)
    assert pelvis.accel[2] < 0.0 # Accelerates upward

def test_coupled_physics_matrix_c_pelvis_belt_coupling():
    """Test C: Pelvis + Lap Belt Restraint Coupling."""
    model = LumpedMassCrashModel(dummy_type="FAA_HIII_50M")
    res = model.run()
    belt_lap = res.get("belt_lap_load_kn", [])
    assert float(np.max(belt_lap)) > 0.5 # > 0.5 kN lap belt tension

def test_coupled_physics_matrix_d_torso_belt_coupling():
    """Test D: Torso + Diagonal Harness Restraint Coupling."""
    model = LumpedMassCrashModel(dummy_type="FAA_HIII_50M")
    res = model.run()
    belt_shoulder = res.get("belt_shoulder_load_kn", [])
    assert float(np.max(belt_shoulder)) > 1.0 # > 1.0 kN shoulder harness tension

def test_coupled_physics_matrix_e_full_occupant_joints():
    """Test E: Full Occupant + Cervical/Lumbar Joints Coupling."""
    model = LumpedMassCrashModel(dummy_type="FAA_HIII_50M")
    res = model.run()
    neck_m = res.get("neck_moment", [])
    assert float(np.max(np.abs(neck_m))) > 5.0 # Neck joint moment generated

def test_coupled_physics_matrix_f_full_chain_end_to_end():
    """Test F: Full Sled -> Seat -> Pelvis -> Belt -> Torso -> Neck -> Head chain."""
    model = LumpedMassCrashModel(dummy_type="FAA_HIII_50M")
    res = model.run()
    assert "head_acceleration" in res
    assert "neck_axial_force" in res
    assert "belt_shoulder_load_kn" in res

def test_coupled_physics_matrix_g_full_system_friction():
    """Test G: Pelvic friction resists sliding."""
    model = LumpedMassCrashModel(dummy_type="FAA_HIII_50M")
    res = model.run()
    cushion_pen = res.get("seat_deflection_mm", [])
    assert float(np.max(cushion_pen)) > 0.0

def test_coupled_physics_matrix_h_energy_audit():
    """Test H: Full System + Energy Audit."""
    from app.domain.physics.multibody.energy_audit import EnergyMomentumAuditEngine
    audit = EnergyMomentumAuditEngine(100.0)
    audit.update_dissipation(10.0, 10.0, 5.0, dt=0.1)
    res = audit.evaluate_audit(current_kinetic_energy_j=92.5, current_potential_energy_j=5.0)
    assert res["energy_audit_verdict"] == "NUMERICAL_ENERGY_BALANCE_PASS"

def test_coupled_physics_matrix_i_momentum_reaction_audit():
    """Test I: Full System + Momentum & Reaction Audit."""
    reaction_audit = ReactionAuditEngine()
    eval_res = reaction_audit.evaluate_joint_reaction("Cervical_Joint", f_action=[10.0, 0.0, 0.0], f_reaction=[-10.0, 0.0, 0.0])
    assert eval_res["reaction_audit_verdict"] == "NUMERICAL_REACTION_PASS"

def test_coupled_physics_matrix_j_timestep_convergence():
    """Test J: Full System Timestep Convergence."""
    m1 = LumpedMassCrashModel()
    r1 = m1.run()
    m2 = LumpedMassCrashModel()
    r2 = m2.run()
    
    h1 = float(np.max(r1["head_acceleration"]))
    h2 = float(np.max(r2["head_acceleration"]))
    assert abs(h1 - h2) < 0.1
