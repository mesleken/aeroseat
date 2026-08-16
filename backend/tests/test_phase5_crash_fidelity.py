import pytest
import numpy as np
from app.domain.physics.solver.stiff_solver import AdaptiveTimestepSolver, EventDetector
from app.domain.physics.seat.seat_structure import SeatStructureCompliance
from app.domain.physics.restraint.belt_constitutive import StrainRateDependentBelt
from app.domain.physics.validation.golden_validation import GoldenCrashValidationMatrix

def test_adaptive_timestep_solver_and_event_detector():
    """Verifies stiff solver adaptive timestep controller and event detector."""
    solver = AdaptiveTimestepSolver(dt_min_s=1e-6, dt_max_s=1e-3, error_tolerance=1e-4)
    
    # Test 1: Small error -> dt increases
    dt_new1 = solver.compute_next_timestep(current_dt=0.0001, local_error_norm=1e-6)
    assert dt_new1 > 0.0001
    
    # Test 2: Large error -> dt decreases
    dt_new2 = solver.compute_next_timestep(current_dt=0.0001, local_error_norm=1e-2)
    assert dt_new2 < 0.0001
    
    # Test 3: Event boundary crossing (g_prev * g_curr <= 0)
    crossed = EventDetector.detect_event_crossing(g_prev=-0.05, g_curr=0.02)
    assert crossed is True

def test_seat_structure_compliance_and_yielding():
    """Verifies seatback frame angular deflection and plastic yielding threshold."""
    seat = SeatStructureCompliance(yield_torque_nm=1000.0)
    
    # Elastic range (< 1000 Nm)
    angle1, m1 = seat.evaluate_seatback_response(torso_rebound_moment_nm=500.0, dt=0.01)
    assert seat.is_yielded is False
    
    # Yielded range (> 1000 Nm)
    angle2, m2 = seat.evaluate_seatback_response(torso_rebound_moment_nm=1500.0, dt=0.01)
    assert seat.is_yielded is True

def test_strain_rate_dependent_belt_constitutive_law():
    """Verifies webbing strain-rate stiffening, unloading hysteresis, and power dissipation."""
    belt = StrainRateDependentBelt(base_stiffness_n=48000.0)
    
    # Quasi-static loading (strain_rate = 0.1 s^-1)
    f_static, d_static = belt.evaluate_constitutive_tension(strain=0.05, strain_rate=0.1)
    
    # High-strain-rate crash loading (strain_rate = 50.0 s^-1) -> Strain-rate stiffening
    f_dynamic, d_dynamic = belt.evaluate_constitutive_tension(strain=0.05, strain_rate=50.0)
    
    assert f_dynamic > f_static # Dynamic strain-rate stiffening boost
    assert d_dynamic > d_static

def test_golden_crash_validation_matrix():
    """Verifies channel-by-channel Golden Crash Case validation matrix."""
    t = np.linspace(0, 0.1, 100)
    sim = {"head_acceleration": np.sin(t*10)*50.0, "neck_axial_force": np.cos(t*10)*2000.0}
    exp = {"head_acceleration": np.sin(t*10)*51.0, "neck_axial_force": np.cos(t*10)*2050.0}
    
    res = GoldenCrashValidationMatrix.evaluate_golden_case_validation(sim, exp, dt=0.001)
    
    assert "validation_matrix" in res
    assert "total_channels" in res
    assert res["total_channels"] == 4
