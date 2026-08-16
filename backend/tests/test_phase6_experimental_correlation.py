import pytest
import numpy as np
from app.domain.physics.validation.physics_verification_matrix import PhysicsVerificationMatrixEngine
from app.domain.physics.validation.digital_test_replay import DigitalTestReplayEngine

def test_physics_verification_matrix_convergence_study():
    """Verifies systematic multi-timestep convergence study."""
    res = PhysicsVerificationMatrixEngine.run_convergence_study(timesteps=[0.001, 0.0005, 0.00025])
    
    assert res["verification_matrix_status"] == "NUMERICAL_CONVERGENCE_ESTABLISHED"
    assert len(res["convergence_study_results"]) == 3
    assert "convergence_summary" in res

def test_digital_test_replay_calibration_vs_validation_split():
    """Verifies digital test replay with strict calibration vs blind validation dataset split."""
    t = np.linspace(0, 0.1, 100)
    sim = {"head_acceleration": np.sin(t*10)*50.0}
    calib = {"head_acceleration": np.sin(t*10)*51.0}
    valid = {"head_acceleration": np.sin(t*10)*52.0}
    
    replay = DigitalTestReplayEngine(calibration_dataset=calib, validation_dataset=valid)
    res = replay.execute_digital_test_replay(sim, dt=0.001)
    
    assert res["digital_test_replay_status"] == "REPLAY_MATCHING_COMPLETE"
    assert "calibration_dataset_correlation" in res
    assert "blind_validation_dataset_correlation" in res
    assert "AeroSeat has established a high-fidelity numerical verification baseline" in res["audit_statement"]
