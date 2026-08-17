import pytest
import numpy as np

from app.domain.physics.simulation_runner import GrandAssemblySimulationRunner, SimulationConfig, SimulationRunResult

def test_grand_assembly_simulation_full_run():
    """
    Verifies the end-to-end execution of the Grand Assembly Simulation Pipeline:
    - Pre-processing (Snap-to-Track, 1G Settling, Shrink-Wrap routing)
    - Transient crash ODE solving (0 -> 250 ms)
    - Biomechanical HIC calculation and FAA compliance audit
    - Frame State JSON generation for WebGL / Three.js
    """
    config = SimulationConfig(
        pulse_type="FORWARD_16G",
        peak_g=16.0,
        rise_time_ms=90.0,
        total_duration_ms=250.0,
        setback_inches=22.9528, # 583 mm
        enable_1g_settling=True,
        enable_shrink_wrap_belt=True
    )
    
    runner = GrandAssemblySimulationRunner(config=config)
    result = runner.run_full_simulation()
    
    assert result.is_completed is True
    assert result.hic15 > 0.0
    assert result.max_head_accel_g > 0.0
    assert result.max_lumbar_load_n > 0.0
    assert result.max_femur_load_n > 0.0
    assert result.max_belt_tension_lb > 0.0
    assert result.max_head_excursion_mm > 0.0
    
    # Check Pillar Sub-Reports
    assert result.mounting_report["snap_alignment"]["is_snapped"] is True
    assert result.settling_report["is_equilibrium_reached"] is True
    assert result.belt_routing_report["lap_belt"]["is_penetration_free"] is True
    assert result.belt_routing_report["shoulder_harness"]["is_penetration_free"] is True
    assert "statutory_summary" in result.faa_compliance_report

    # Check Frame State JSON
    frame_json = result.frame_state_json
    assert frame_json["metadata"]["engine"] == "AeroSeat CAE Grand Assembly Pipeline"
    assert frame_json["metadata"]["total_frames"] > 50
    assert len(frame_json["animation_timeline"]) > 50
    assert len(frame_json["belt_splines_3d"]["lap_belt_points_m"]) > 10
    assert len(frame_json["belt_splines_3d"]["shoulder_belt_points_m"]) > 10
    assert "mounting_fittings" in frame_json

def test_front_row_exemption_in_simulation_runner():
    """
    Verifies that when an economy seat has setback >= 42 inches (e.g. 44 inches),
    the simulation runner grants front-row HIC exemption per FAA AC 25.562-1B.
    """
    config = SimulationConfig(
        pulse_type="FORWARD_16G",
        setback_inches=44.0, # Front-row exemption satisfied
        seat_class="economy",
        is_metallic_load_path=True
    )
    
    runner = GrandAssemblySimulationRunner(config=config)
    result = runner.run_full_simulation()
    
    assert result.is_completed is True
    exemption_info = result.faa_compliance_report["front_row_exemption"]
    assert exemption_info["is_exempt"] is True
    assert "PASS" in exemption_info["reason"]
