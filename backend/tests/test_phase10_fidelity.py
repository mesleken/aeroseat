import pytest
import numpy as np
from app.domain.physics.lumped_mass_model import (
    LumpedMassCrashModel,
    OccupantSegmentConfig,
    DUMMY_PRESETS,
    BeltAnchorGeometry,
    RestraintAndStiffnessConfig
)
from app.domain.physics.multibody.constitutive import ConstitutiveModels
from app.domain.injury_metrics import apply_oc_moment_correction, calculate_nij, compute_all_injury_metrics
from app.domain.physics.monte_carlo_engine import MonteCarloEngine

def test_phase10_001_3d_belt_vector_resolution():
    """Verifies that 1D restraint tension is correctly resolved into 3D Cartesian vectors."""
    tension = 5000.0 # 5 kN
    body_pos = (0.0, 0.0, 0.0)
    anchor_pos = (3.0, 4.0, 0.0) # Length = 5.0 m, unit vector = [0.6, 0.8, 0.0]
    
    fx, fy, fz = ConstitutiveModels.resolve_belt_force_3d(tension, body_pos, anchor_pos)
    
    assert abs(fx - 3000.0) < 1e-3
    assert abs(fy - 4000.0) < 1e-3
    assert abs(fz - 0.0) < 1e-3
    assert abs(np.sqrt(fx**2 + fy**2 + fz**2) - tension) < 1e-3

def test_phase10_002_hunt_crossley_joint_mechanics():
    """Verifies Hunt-Crossley non-linear joint compliance and smooth boundary dissipation."""
    k = 25000.0
    c = 800.0
    
    # Delta = 0 -> Force = 0
    f0 = ConstitutiveModels.hunt_crossley_joint(0.0, 1.0, k, c)
    assert f0 == 0.0
    
    # Delta = 0.02 m vs Delta = 0.04 m (exponent 1.5 -> (0.04/0.02)^1.5 = 2^1.5 ~ 2.828x increase in stiffness)
    f1 = ConstitutiveModels.hunt_crossley_joint(0.02, 0.0, k, c, exponent=1.5)
    f2 = ConstitutiveModels.hunt_crossley_joint(0.04, 0.0, k, c, exponent=1.5)
    assert f2 / f1 > 2.7

def test_phase10_003_occipital_condyle_moment_correction():
    """Verifies SAE J211 / FAA AC 20-146A Occipital Condyle moment transformation."""
    my_loadcell = np.array([120.0, 150.0, 180.0])
    fx_shear = np.array([2000.0, 2500.0, 3000.0])
    d_oc = 0.01778 # 0.70 inches
    
    my_oc = apply_oc_moment_correction(my_loadcell, fx_shear, d_oc_m=d_oc)
    expected = my_loadcell - d_oc * fx_shear
    
    np.testing.assert_allclose(my_oc, expected, atol=1e-5)
    assert np.all(my_oc < my_loadcell) # OC correction reduces positive flexion moment

def test_phase10_004_full_anthropometric_mass_77kg():
    """Verifies that the FAA Hybrid III 50M dummy configuration matches full 77.7 kg crash test mass."""
    occ_50m = DUMMY_PRESETS["FAA_HIII_50M"]
    total_mass = occ_50m.total_dummy_mass_kg
    
    # Total mass must be within [76.5, 78.5] kg (171.3 lbs standard)
    assert 76.5 <= total_mass <= 78.5
    assert occ_50m.tibia_left_mass > 0.0
    assert occ_50m.foot_left_mass > 0.0
    assert occ_50m.arms_mass > 0.0

def test_phase10_005_monte_carlo_bepu_uncertainty_quantification():
    """Verifies that the Monte Carlo BEPU Engine computes statistically sound 95% confidence bounds."""
    bepu = MonteCarloEngine(base_pulse_type="FORWARD_16G", dummy_type="FAA_HIII_50M", n_samples=15, seed=123)
    results = bepu.run_bepu_analysis()
    
    assert results["n_samples"] == 15
    metrics = results["metrics"]
    
    # HIC15 statistics
    hic_stat = metrics["hic15"]
    assert hic_stat["mean"] > 0.0
    assert hic_stat["std"] > 0.0
    assert hic_stat["p5"] <= hic_stat["p50_median"] <= hic_stat["p95"]
    assert len(hic_stat["ci_95_bounds"]) == 2
    assert hic_stat["compliance_probability_pct"] >= 90.0
    assert hic_stat["bepu_status"] == "COMPLIANT_HIGH_CONFIDENCE"
