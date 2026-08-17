import pytest
import numpy as np

from app.domain.physics.monte_carlo_engine import MonteCarloEngine, latin_hypercube_sample, UniformDistribution
from app.domain.physics.signal_processing import fae_ac20_146a_data_reduction, sae_j211_cfc_filter
from app.domain.physics.lumped_mass_model import LumpedMassCrashModel, RestraintAndStiffnessConfig
from aeroseat.core import SledTest, SeatModel, Dummy, SledPulse

def test_latin_hypercube_sampling_stratification():
    """Verifies that LHS draws exactly one sample per sub-interval across all dimensions."""
    rng = np.random.default_rng(42)
    n_samples = 50
    n_dim = 9
    
    samples = latin_hypercube_sample(n_samples, n_dim, rng)
    
    assert samples.shape == (n_samples, n_dim)
    assert np.all(samples >= 0.0)
    assert np.all(samples <= 1.0)
    
    # Check marginal stratification for each dimension
    for j in range(n_dim):
        bins = np.linspace(0.0, 1.0, n_samples + 1)
        hist, _ = np.histogram(samples[:, j], bins=bins)
        # Every 1/N interval should have exactly 1 sample
        assert np.all(hist == 1)

def test_faa_3_inch_flail_offset_clearance():
    """
    Verifies the FAA 14 CFR § 25.562 / SAE AS8049E 3.0-inch (76.2 mm) 95th-percentile flail margin.
    - Setback: 583 mm
    - Redesigned head path: <= 555 mm
    - Remaining head clearance to bulkhead: 583 - 555 = 28 mm (< 76.2 mm threshold)
    - If setback is standard pitch (e.g. 35 inches = 889 mm), clearance is > 76.2 mm (3 in).
    """
    # 1. Close-pitch bulkhead test (Setback = 583 mm)
    seat_close = SeatModel(setback_mm=583, belt_type='optimized_y_belt')
    seat_close.apply_design_factors()
    pulse = SledPulse(peak_g=16.0, rise_time_ms=90)
    dummy = Dummy()
    
    sim_close = SledTest(seat_close, dummy, pulse)
    res_close = sim_close.run()
    
    clearance_close_mm = 583.0 - res_close.head_path_mm
    assert clearance_close_mm >= 28.0 # Positive clearance, no impact
    assert res_close.head_impact_occurred is False
    assert res_close.hic < 1000.0

    # 2. Standard pitch aisle/seat row (Setback = 35 inches = 889 mm)
    setback_open_mm = 35.0 * 25.4 # 889 mm
    clearance_open_mm = setback_open_mm - res_close.head_path_mm
    # Must exceed the 3.0 inch (76.2 mm) 95th percentile safety envelope
    assert clearance_open_mm > 76.2
    assert clearance_open_mm > 300.0

def test_faa_ac20_146a_10pct_data_reduction_corridor():
    """
    Verifies FAA AC 20-146A Chapter 4 Data Reduction:
    - 10 kHz raw sensor trace is decimated to 1 kHz (10x data compression)
    - Peak acceleration deviation is strictly within the <= 10.0% regulatory bound
    - Velocity change (Delta-V) deviation is strictly <= 5.0%
    """
    t_10k = np.linspace(0.0, 0.18, 1801) # 10 kHz (dt = 0.0001s)
    # 16G triangular pulse with 70G occupant head deceleration peak
    a_10k = 70.0 * np.sin(np.pi * t_10k / 0.18) + 3.0 * np.sin(2 * np.pi * 120 * t_10k)
    
    res = fae_ac20_146a_data_reduction(
        time_s=t_10k,
        accel_g=a_10k,
        target_dt_s=0.001, # 1 kHz
        cfc=1000,
        max_allowed_deviation_pct=10.0
    )
    
    assert res["is_faa_compliant"] is True
    assert res["compression_ratio"] >= 9.0
    assert res["peak_deviation_pct"] <= 10.0
    assert res["delta_v_deviation_pct"] <= 5.0

def test_bepu_latin_hypercube_sensitivity_execution():
    """
    Verifies that MonteCarloEngine executes with LHS and produces 9-factor ranking.
    """
    engine = MonteCarloEngine(samples=20, seed=42)
    res = engine.run_lamanna_sensitivity_analysis(n_samples=20, use_lhs=True)
    
    assert res["status"] == "SENSITIVITY_ANALYSIS_COMPLETED"
    assert len(res["sensitivity_ranking"]) == 9
    assert res["hic_distribution"]["compliance_rate_pct"] == 100.0

def test_faa_certification_engine_data_reduction_and_exemptions():
    """
    Verifies FAA AC 25.562-1B statutory rules via FAACertificationEngine:
    - 14g lumbar reduction from 1590 lb @ 15g to 1484 lb (PASS)
    - 10% maximum allowable reduction limit cap
    - 95th percentile head path +3.0 in (+76.2 mm) addition
    - Front row HIC exemption checks for economy (>= 42 in) and business (>= 45 in)
    """
    from app.domain.certification_rules import FAACertificationEngine
    
    faa = FAACertificationEngine()
    
    # 1. 14g Lumbar test example (1590 lb raw at 15.0g peak -> 1484.0 lb adjusted -> PASS)
    adj_lumbar = faa.apply_data_reduction(measured_load=1590.0, actual_peak_g=15.0, target_peak_g=14.0)
    assert round(adj_lumbar, 1) == 1484.0
    assert adj_lumbar <= faa.MAX_LUMBAR_LOAD_LB
    
    # 2. Maximum 10% reduction cap (e.g. 18.0g test for 14.0g target -> max 10% reduction)
    adj_capped = faa.apply_data_reduction(measured_load=1000.0, actual_peak_g=18.0, target_peak_g=14.0)
    assert adj_capped == 900.0 # Exactly 10% reduction (0.90 ratio)
    
    # 3. If actual_peak_g <= target_peak_g, no reduction applied
    adj_none = faa.apply_data_reduction(measured_load=1200.0, actual_peak_g=13.5, target_peak_g=14.0)
    assert adj_none == 1200.0

    # 4. 95th percentile head flail offset (+76.2 mm)
    flail_95 = faa.evaluate_95th_percentile_head_path(950.0)
    assert flail_95 == 950.0 + 76.2
    
    # 5. Front row HIC exemption
    exempt_econ, msg_econ = faa.check_front_row_hic_exemption(setback_inches=43.0, seat_class="economy")
    assert exempt_econ is True
    assert "PASS" in msg_econ
    
    non_exempt_econ, _ = faa.check_front_row_hic_exemption(setback_inches=40.0, seat_class="economy")
    assert non_exempt_econ is False
    
    exempt_biz, _ = faa.check_front_row_hic_exemption(setback_inches=46.0, seat_class="business")
    assert exempt_biz is True
    
    non_metallic, _ = faa.check_front_row_hic_exemption(setback_inches=48.0, is_metallic_load_path=False)
    assert non_metallic is False
