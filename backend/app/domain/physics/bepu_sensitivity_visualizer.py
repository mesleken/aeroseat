import sys
import os
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

import numpy as np
from typing import Dict, Any

from app.domain.physics.monte_carlo_engine import MonteCarloEngine, UniformDistribution, GaussianDistribution

def generate_bepu_statistical_report(n_samples: int = 30, seed: int = 42) -> str:
    """
    Executes BEPU Sensitivity & Statistical Distribution Analysis on the 9 Lamanna (2019) Factors
    and formats an ASCII/Markdown engineering report with Tornado chart and HIC histogram.
    """
    engine = MonteCarloEngine(samples=n_samples, seed=seed)
    
    # Register 9 Lamanna factors
    engine.add_parameter("APX_belt_anchor_x", UniformDistribution(26.0, 45.0))
    engine.add_parameter("APY_belt_anchor_y", UniformDistribution(44.0, 88.0))
    engine.add_parameter("D1_rear_beam_thick", UniformDistribution(2.0, 3.0))
    engine.add_parameter("D2_rear_leg_frame_thick", UniformDistribution(3.0, 4.5))
    engine.add_parameter("D3_rear_leg_body_thick", UniformDistribution(1.8, 2.7))
    engine.add_parameter("D4_shock_absorber_thick", UniformDistribution(2.0, 3.2))
    engine.add_parameter("D5_rear_leg_frame_width", UniformDistribution(18.0, 20.0))
    engine.add_parameter("D6_reinf_beam_thick", UniformDistribution(1.0, 1.5))
    engine.add_parameter("D7_reinf_beam_len", UniformDistribution(150.0, 250.0))

    results = engine.run_lamanna_sensitivity_analysis(n_samples=n_samples)
    
    hic_stat = results["hic_distribution"]
    exc_stat = results["head_excursion_distribution_mm"]
    acc_stat = results["peak_head_acceleration_g"]
    ranking = results["sensitivity_ranking"]

    lines = []
    lines.append("=" * 80)
    lines.append("   AEROSEAT BEPU MONTE CARLO SENSITIVITY & STATISTICAL DISTRIBUTION REPORT")
    lines.append("   Reference: Lamanna et al. (2019) / Caputo et al. (2018) Geven S.p.A.")
    lines.append("=" * 80)
    lines.append(f"  Total Monte Carlo Iterations: {results['n_samples']}")
    lines.append(f"  Crash Pulse: 16G Triangular (90ms Rise Time)")
    lines.append(f"  Obstacle Setback: 583 mm (23 in)")
    lines.append("")
    lines.append("--- 1. INJURY CRITERIA & OCCUPANT KINEMATICS DISTRIBUTION ---")
    lines.append(f"  HIC15 Mean +/- Std         : {hic_stat['mean']:.1f} +/- {hic_stat['std']:.1f}")
    lines.append(f"  HIC15 95th Percentile (P95): {hic_stat['p95']:.1f} (FAA Limit: 1000.0) -> {'COMPLIANT' if hic_stat['p95'] < 1000 else 'NON-COMPLIANT'}")
    lines.append(f"  HIC15 Regulatory Compliance: {hic_stat['compliance_rate_pct']:.1f}%")
    lines.append(f"  Head Excursion Mean (mm)   : {exc_stat['mean']:.1f} mm (Clearance: {583.0 - exc_stat['mean']:.1f} mm)")
    lines.append(f"  Head Excursion P95 (mm)    : {exc_stat['p95']:.1f} mm (Max: {exc_stat['max']:.1f} mm)")
    lines.append(f"  Peak Head Accel P95 (g)    : {acc_stat['p95']:.1f} g")
    lines.append("")
    lines.append("--- 2. TORNADO SENSITIVITY RANKING (PEARSON CORRELATION WITH HIC) ---")
    lines.append(f"  {'Rank':<5} {'Factor':<32} {'Corr (HIC)':<12} {'Corr (Path)':<12} {'Tornado Bar'}")
    lines.append("  " + "-" * 76)
    
    for idx, item in enumerate(ranking, 1):
        corr_h = item["correlation_with_hic"]
        corr_e = item["correlation_with_excursion"]
        bar_len = int(abs(corr_h) * 25)
        bar_str = ("#" * bar_len).ljust(25)
        lines.append(f"  {idx:<5} {item['factor']:<32} {corr_h:+0.3f}        {corr_e:+0.3f}        [{bar_str}]")

    lines.append("")
    lines.append("--- 3. HIC15 FREQUENCY HISTOGRAM ---")
    counts = hic_stat["histogram_counts"]
    edges = hic_stat["histogram_bin_edges"]
    max_c = max(counts) if counts else 1
    for k in range(len(counts)):
        b_low = edges[k]
        b_high = edges[k + 1]
        bar_stars = "=" * int((counts[k] / max_c) * 35)
        lines.append(f"  [{b_low:6.1f} - {b_high:6.1f}] : {counts[k]:3d} ({counts[k]/n_samples*100:4.1f}%) {bar_stars}")

    lines.append("=" * 80)
    return "\n".join(lines)

if __name__ == "__main__":
    report = generate_bepu_statistical_report(n_samples=25)
    print(report)
