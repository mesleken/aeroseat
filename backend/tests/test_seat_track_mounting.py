import pytest
import numpy as np

from app.domain.physics.seat.seat_track_mounting import SeatTrackMountingEngine, Dummy1GSettlingSolver
from app.domain.physics.seat.seat_structure import SeatMountingCompliance

def test_snap_to_track_kinematic_alignment():
    """
    Verifies the Snap-to-Track automated kinematic solver:
    - Datum Z=0 alignment
    - Lateral snapping to standard 19.0-inch (482.6 mm) track pitch
    - Longitudinal quantization to discrete 1.0-inch (25.4 mm) hole detents
    """
    engine = SeatTrackMountingEngine(track_pitch_inches=19.0, hole_pitch_inches=1.0)
    
    # Raw CAD input feet with arbitrary offsets and minor misalignment
    raw_fl = [382.1, -245.0, 12.5]
    raw_fr = [381.8, 240.0, 12.0]
    raw_rl = [0.4, -243.0, 12.2]
    raw_rr = [-0.2, 242.0, 12.4]
    
    snap_res = engine.snap_to_track(raw_fl, raw_fr, raw_rl, raw_rr)
    
    assert snap_res.is_snapped is True
    coords = snap_res.snapped_coordinates
    
    # Ground plane Z = 0
    assert coords.front_left[2] == 0.0
    assert coords.front_right[2] == 0.0
    assert coords.rear_left[2] == 0.0
    assert coords.rear_right[2] == 0.0
    
    # Lateral Y positions snapped to +/- 19.0/2 inches (+/- 241.3 mm)
    assert coords.front_left[1] == -241.3
    assert coords.front_right[1] == 241.3
    assert coords.rear_left[1] == -241.3
    assert coords.rear_right[1] == 241.3
    
    # Discrete hole detent quantization
    assert snap_res.discrete_hole_indices["rear_left_hole"] == 0
    assert snap_res.discrete_hole_indices["rear_right_hole"] == 0
    assert snap_res.discrete_hole_indices["front_left_hole"] == 15 # 15 inches wheelbase

def test_ms33601_four_point_fitting_reactions():
    """
    Verifies dynamic 4-point reaction force resolution during 16G forward impact:
    - High tension pull-out forces at the rear fittings
    - Downward compressive forces at the front fittings
    - Margin of safety against MS33601 single-stud limit
    """
    engine = SeatTrackMountingEngine()
    
    # Typical 16G forward occupant loading
    f_occupant_x = 12000.0 # 12 kN forward
    f_occupant_z = 0.0
    m_pitch = 3500.0 # 3.5 kNm forward pitch moment
    
    reactions = engine.evaluate_fitting_reactions(
        occupant_fx_n=f_occupant_x,
        occupant_fz_n=f_occupant_z,
        overturning_moment_my_nm=m_pitch,
        seat_mass_kg=18.0,
        sled_accel_x_g=16.0,
        wheelbase_leg_spacing_mm=381.0 # 15 inches
    )
    
    # Rear legs undergo high upward pullout tension (negative Fz)
    assert reactions.rear_left_fz_n < 0.0
    assert reactions.rear_right_fz_n < 0.0
    assert reactions.max_pullout_load_n > 5000.0
    
    # Front legs undergo downward compression (positive Fz)
    assert reactions.front_left_fz_n > 0.0
    assert reactions.front_right_fz_n > 0.0
    
    # Margin of safety against 35 kN MS33601 pullout limit
    assert reactions.fitting_margin_of_safety > 1.0
    assert reactions.is_fitting_yielded is False

def test_14_cfr_25_562_floor_warpage_fixture():
    """
    Verifies 10-deg pitch / 10-deg roll floor warpage fixture pre-stress calculation.
    """
    engine = SeatTrackMountingEngine()
    warpage_res = engine.evaluate_10deg_floor_warpage(
        pitch_warpage_deg=10.0,
        roll_warpage_deg=10.0
    )
    
    assert warpage_res["is_warpage_compliant"] is True
    assert warpage_res["differential_dz_mm"] > 50.0 # Over 50mm twisted displacement
    assert warpage_res["pre_stress_force_per_leg_n"] > 0.0

def test_dummy_1g_gravity_settling_solver():
    """
    Verifies 1G static gravity settling simulation:
    - Settles ATD into foam to reach static equilibrium
    - Final equilibrium penetration matches F_gravity / k_foam
    - Eliminates initial penetration spikes
    """
    settle_res = Dummy1GSettlingSolver.simulate_1g_settling(
        occupant_mass_kg=77.0,
        cushion_foam_k=95000.0,
        cushion_damping_c=3200.0,
        initial_drop_height_mm=20.0
    )
    
    # Static gravity = 77 * 9.80665 = 755.1 N
    # Expected penetration = 755.1 / 95000 = 7.95 mm ~ 8.0 mm
    assert settle_res["is_equilibrium_reached"] is True
    assert 7.0 <= settle_res["final_equilibrium_penetration_mm"] <= 9.0
    assert settle_res["static_pre_load_n"] > 750.0
