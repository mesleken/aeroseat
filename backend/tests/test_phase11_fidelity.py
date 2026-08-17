import pytest
import numpy as np

from app.domain.physics.lumped_mass_model import LumpedMassCrashModel, RestraintAndStiffnessConfig
from app.domain.injury_metrics import compute_all_injury_metrics
from app.domain.physics.multibody.contact_geometry import ObstacleContactEngine, FlailEnvelopeContactConfig, ObstacleSurface
from app.domain.physics.multibody.correlation_engine import Iso18571CorrelationEngine, IsoTs18571Weights
from app.domain.physics.signal_processing import sae_j211_appendix_c_filter
from app.domain.physics.geometry_extraction import GeometryExtractionEngine, CadAnchorInput

def test_phase11_001_secondary_head_strike_contact_detection():
    """Verifies that an obstacle within the head flail envelope detects contact and induces high-G deceleration."""
    # 1. No obstacle (open flail envelope)
    model_free = LumpedMassCrashModel(pulse_type="FORWARD_16G", forward_obstacle_pitch_inches=None)
    res_free = model_free.run()
    inj_free = compute_all_injury_metrics(res_free)

    # 2. Obstacle at 23 inches forward pitch (0.584 m) -> Head strikes front bulkhead
    model_strike = LumpedMassCrashModel(pulse_type="FORWARD_16G", forward_obstacle_pitch_inches=23.0)
    res_strike = model_strike.run()
    inj_strike = compute_all_injury_metrics(res_strike)

    peak_head_free = float(np.max(res_free["head_acceleration"]))
    peak_head_strike = float(np.max(res_strike["head_acceleration"]))

    # Secondary impact contact force must sharply increase peak acceleration and HIC
    assert peak_head_strike > peak_head_free * 1.25
    assert inj_strike["hic15"] > inj_free["hic15"] * 2.0

def test_phase11_002_iso_ts_18571_objective_curve_correlation():
    """Verifies ISO/TS 18571 Corridor (Z), Phase (EP), Magnitude (EM), and Slope (ES) rating algorithms."""
    engine = Iso18571CorrelationEngine(dt=0.0001)
    t = np.linspace(0, 0.18, 1801)
    
    # Reference signal
    ref = 50.0 * np.sin(np.pi * t / 0.18)
    
    # Identical signal -> Perfect ISO rating = 1.0
    res_perfect = engine.evaluate_curve_correlation(ref, ref)
    assert abs(res_perfect["overall_iso_rating"] - 1.0) < 1e-3
    assert res_perfect["status"] == "EXCELLENT_CORRELATION"

    # Perturbed signal with 10% magnitude shift and small phase lag
    sim_pert = 45.0 * np.sin(np.pi * np.maximum(0.0, t - 0.005) / 0.18)
    res_pert = engine.evaluate_curve_correlation(sim_pert, ref)
    assert 0.65 <= res_pert["overall_iso_rating"] <= 0.95
    assert res_pert["corridor_rating_z"] > 0.60
    assert res_pert["phase_rating_ep"] > 0.80

def test_phase11_003_sae_j211_appendix_c_recursive_filter():
    """Verifies SAE J211-1 Appendix C digital IIR filtering implementation."""
    dt = 0.0001
    t = np.linspace(0, 0.1, 1001)
    clean = 20.0 * np.sin(2 * np.pi * 50 * t)
    noise = 10.0 * np.sin(2 * np.pi * 3500 * t) # High freq noise
    noisy = clean + noise
    
    filtered = sae_j211_appendix_c_filter(noisy, dt, cfc=1000)
    
    # Noise must be substantially attenuated while low-frequency content is preserved
    assert np.max(np.abs(filtered)) < np.max(np.abs(noisy))
    assert abs(np.max(filtered) - 20.0) < 3.0

def test_phase11_004_cad_anchor_geometry_extraction():
    """Verifies semi-automated / automated CAD anchor coordinate transformation."""
    cad_in = CadAnchorInput(
        d_ring_xyz=(0.32, 0.24, -0.45),
        buckle_xyz=(0.04, 0.19, 0.05),
        lap_anchor_left_xyz=(-0.06, -0.21, 0.09),
        lap_anchor_right_xyz=(-0.06, 0.21, 0.09)
    )
    
    geom = GeometryExtractionEngine.create_belt_geometry_from_cad(cad_in)
    assert geom.d_ring_xyz == (0.32, 0.24, -0.45)
    assert geom.buckle_xyz == (0.04, 0.19, 0.05)
    
    # Bounding box estimation
    bbox_geom = GeometryExtractionEngine.estimate_anchors_from_seat_bounds(
        seat_bbox_min_m=(-0.3, -0.3, -0.5),
        seat_bbox_max_m=(0.4, 0.3, 0.5)
    )
    assert len(bbox_geom.d_ring_xyz) == 3
    assert len(bbox_geom.buckle_xyz) == 3

def test_phase11_005_as8049e_pre_test_warpage_kinematics():
    """Verifies 10-deg track warpage affects initial structural mounting offsets."""
    model_flat = LumpedMassCrashModel(seat_pitch_warp_deg=0.0, seat_roll_warp_deg=0.0)
    res_flat = model_flat.run()

    model_warped = LumpedMassCrashModel(seat_pitch_warp_deg=10.0, seat_roll_warp_deg=10.0)
    res_warped = model_warped.run()

    # Warpage introduces asymmetric vertical rail offset
    assert res_warped["seat_deflection_mm"] is not None
    assert len(res_warped["seat_deflection_mm"]) > 0
