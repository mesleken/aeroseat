import pytest
import numpy as np

from app.domain.physics.restraint.belt_routing_engine import BeltRoutingEngine, BeltNode, BeltPathResult

def test_lap_belt_shrink_wrap_routing():
    """
    Verifies that the lap belt path wraps around the ATD pelvis contour
    without penetrating the pelvis cylinder/ellipsoid.
    """
    engine = BeltRoutingEngine(
        anchor_left_mm=[-300.0, -240.0, 50.0],
        anchor_right_mm=[-300.0, 240.0, 50.0],
        buckle_mm=[-50.0, 0.0, 160.0],
        pelvis_center_mm=[-80.0, 0.0, 140.0],
        pelvis_radius_mm=180.0,
        belt_clearance_mm=5.0
    )
    
    lap_res = engine.generate_lap_belt_path(num_nodes=25)
    
    assert lap_res.belt_type == "LAP_BELT"
    assert len(lap_res.nodes) == 25
    assert lap_res.total_length_mm > 400.0
    assert lap_res.is_penetration_free is True
    assert lap_res.wrap_angle_deg > 60.0
    
    # Check that nodes maintain anterior clearance from pelvis center
    for n in lap_res.nodes:
        # Distance in XY plane from pelvis center
        dist_xy = np.sqrt((n.x - (-80.0))**2 + (n.y - 0.0)**2)
        # Waypoints on the body should satisfy clearance
        if abs(n.y) < 200.0:
            assert dist_xy >= 150.0

def test_shoulder_belt_torso_routing():
    """
    Verifies that the diagonal shoulder harness wraps across the ATD chest
    from seatback D-ring anchor down to the lap buckle without torso penetration.
    """
    engine = BeltRoutingEngine(
        shoulder_anchor_d_ring_mm=[-150.0, -180.0, 950.0],
        buckle_mm=[-50.0, 0.0, 160.0],
        torso_center_mm=[-40.0, 0.0, 580.0],
        chest_radius_mm=160.0,
        belt_clearance_mm=5.0
    )
    
    shoulder_res = engine.generate_shoulder_belt_path(num_nodes=30)
    
    assert shoulder_res.belt_type == "SHOULDER_HARNESS"
    assert len(shoulder_res.nodes) == 30
    assert shoulder_res.total_length_mm > 600.0
    assert shoulder_res.is_penetration_free is True
    
    # Start and End node checks
    assert abs(shoulder_res.nodes[0].z - 950.0) < 50.0
    assert abs(shoulder_res.nodes[-1].z - 160.0) < 50.0

def test_euler_eytelwein_capstan_friction():
    """
    Verifies the Euler-Eytelwein belt friction load transfer across ATD contact:
    T_buckle = T_anchor * exp(-mu * theta)
    """
    engine = BeltRoutingEngine(webbing_friction_coeff=0.18)
    
    # 90 degrees wrap (pi / 2 rad)
    theta_rad = np.pi / 2.0
    frict_res = engine.evaluate_euler_eytelwein_friction(
        tension_anchor_n=5000.0,
        wrap_angle_rad=theta_rad
    )
    
    # Expected ratio = exp(-0.18 * 1.5708) = exp(-0.2827) ~ 0.7537
    expected_t_buckle = 5000.0 * np.exp(-0.18 * theta_rad)
    
    assert abs(frict_res["tension_buckle_n"] - expected_t_buckle) < 1.0
    assert frict_res["frictional_drag_n"] > 1000.0
    assert frict_res["capstan_transmission_ratio"] < 1.0

def test_threejs_points_export_format():
    """
    Verifies that threejs_points_m are scaled from mm to meters [x/1000, y/1000, z/1000].
    """
    engine = BeltRoutingEngine()
    lap_res = engine.generate_lap_belt_path(num_nodes=10)
    
    threejs_pts = lap_res.threejs_points_m
    assert len(threejs_pts) == 10
    
    for pt in threejs_pts:
        assert len(pt) == 3
        # Coordinates in meters should be in reasonable range [-1.5, +1.5]
        assert -1.5 <= pt[0] <= 1.5
        assert -1.5 <= pt[1] <= 1.5
        assert -1.5 <= pt[2] <= 1.5
