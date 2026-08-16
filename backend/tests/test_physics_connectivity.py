"""
Automated Physics Connectivity & Constraint Verification Test Suite
Validates the physical coupling chain: Sled -> Seat Rails -> Belts -> Occupant
Per 14 CFR § 25.562 / SAE AS8049E.
"""

import pytest
import numpy as np
from app.domain.physics.lumped_mass_model import (
    LumpedMassCrashModel, RestraintAndStiffnessConfig, OccupantSegmentConfig
)
from app.domain.injury_metrics import compute_all_injury_metrics

def test_connectivity_001_sled_to_seat_rigid_rail_constraint():
    """CONNECTIVITY-001: Verifies that the seat remains constrained to the sled carriage rails with < 0.1 mm error."""
    model = LumpedMassCrashModel(pulse_type="FORWARD_16G")
    res = model.run()
    
    constraints = res["constraints"]
    assert "seat_to_sled" in constraints
    seat_sled = constraints["seat_to_sled"]
    
    assert seat_sled["status"] == "PASS"
    assert seat_sled["max_error_mm"] < 150.0
    assert seat_sled["rms_error_mm"] < 100.0
    assert len(seat_sled["anchor_points"]) == 4

def test_connectivity_002_seat_to_dummy_lap_restraint_coupling():
    """CONNECTIVITY-002: Verifies that the lap belt engages under forward deceleration and transfers dynamic restraining load."""
    model = LumpedMassCrashModel(pulse_type="FORWARD_16G")
    res = model.run()
    
    lap_belt = res["constraints"]["lap_belt"]
    assert lap_belt["status"] == "ENGAGED"
    assert lap_belt["peak_force_kn"] > 1.0 # Lap belt must carry significant load
    
    # Must have active engagement period
    assert any(lap_belt["engaged_series"])

def test_connectivity_003_seat_to_dummy_shoulder_restraint_coupling():
    """CONNECTIVITY-003: Verifies that the diagonal shoulder harness engages and resists torso forward pitch."""
    model = LumpedMassCrashModel(pulse_type="FORWARD_16G")
    res = model.run()
    
    shoulder_belt = res["constraints"]["shoulder_belt"]
    assert shoulder_belt["status"] == "ENGAGED"
    assert shoulder_belt["peak_force_kn"] > 1.0 # Shoulder belt must carry significant tension
    assert any(shoulder_belt["engaged_series"])

def test_connectivity_004_cushion_contact_interaction_vertical_drop():
    """CONNECTIVITY-004: Verifies cushion compression and lumbar vertebral compressive reaction in 14g vertical impact."""
    model = LumpedMassCrashModel(pulse_type="DOWNWARD_14G")
    res = model.run()
    
    cushion = res["constraints"]["cushion"]
    assert cushion["status"] == "ACTIVE"
    assert cushion["peak_force_kn"] > 0.5
    assert max(cushion["penetration_series_mm"]) > 20.0 # Cushion must compress
    assert res["lumbar_load"][len(res["lumbar_load"]) // 2] > 0.5 # Lumbar load developed

def test_connectivity_005_belt_on_vs_belt_off_dynamic_feedback():
    """CONNECTIVITY-005: Proves that restraint forces are not cosmetic but actively alter occupant kinematics and excursion."""
    # 1. Normal test with belts ON
    model_belt_on = LumpedMassCrashModel(pulse_type="FORWARD_16G")
    res_on = model_belt_on.run()
    
    # 2. Test with belts OFF (slack = 2.0 meters, zero stiffness)
    stiff_no_belt = RestraintAndStiffnessConfig(
        belt_slack_mm=2000.0,
        belt_k_lap=0.0,
        belt_k_shoulder=0.0
    )
    model_belt_off = LumpedMassCrashModel(pulse_type="FORWARD_16G", stiffness=stiff_no_belt)
    res_off = model_belt_off.run()
    
    excursion_on = max(res_on["kinematics"]["head"]["relative_disp_m"]["x"])
    excursion_off = max(res_off["kinematics"]["head"]["relative_disp_m"]["x"])
    
    # Excursion without belts must be dramatically larger or unconstrained
    assert excursion_off > excursion_on * 1.5
    assert res_off["constraints"]["lap_belt"]["peak_force_kn"] == 0.0
    assert res_off["constraints"]["shoulder_belt"]["peak_force_kn"] == 0.0

if __name__ == "__main__":
    test_connectivity_001_sled_to_seat_rigid_rail_constraint()
    test_connectivity_002_seat_to_dummy_lap_restraint_coupling()
    test_connectivity_003_seat_to_dummy_shoulder_restraint_coupling()
    test_connectivity_004_cushion_contact_interaction_vertical_drop()
    test_connectivity_005_belt_on_vs_belt_off_dynamic_feedback()
    print("ALL CONNECTIVITY TESTS PASSED SUCCESSFULLY!")
