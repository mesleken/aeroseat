import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class SpragueGeersResult:
    """Sprague & Geers Metric Output per FAA AC 20-146A Appendix B."""
    sg_magnitude_m: float      # SG_M (Magnitude Error)
    sg_phase_p: float          # SG_P (Phase Error)
    sg_comprehensive_c: float  # SG_C (Comprehensive Combined Error)
    peak_diff_pct: float       # Peak value percentage difference
    is_faa_compliant: bool     # True if SG_C <= 0.10 (10% FAA tolerance)
    status: str

@dataclass
class IsoTs18571Weights:
    """Standard ISO/TS 18571:2014/2024 Curve Comparison Metric Weights."""
    w_corridor: float = 0.40  # Corridor fit rating (Z)
    w_phase: float = 0.20     # Phase alignment rating (E_P)
    w_magnitude: float = 0.20 # Area / magnitude rating (E_M)
    w_slope: float = 0.20     # Slope / waveform shape derivative rating (E_S)

class FAA_AC20_146A_CorrelationEngine:
    """
    Official FAA AC 20-146A (Appendix B) Sprague & Geers Dynamic Seat Model Correlation Engine.
    Used by FAA Aircraft Certification Offices (ACO) for certification by analysis.
    """

    @staticmethod
    def _integrate_trapezoid(arr: np.ndarray, dt: float) -> float:
        if len(arr) < 2:
            return 0.0
        if hasattr(np, 'trapezoid'):
            return float(np.trapezoid(arr, dx=dt))
        elif hasattr(np, 'trapz'):
            return float(np.trapz(arr, dx=dt))
        return float(np.sum(0.5 * (arr[:-1] + arr[1:]) * dt))

    @classmethod
    def evaluate_sprague_geers(
        cls,
        sim_signal: np.ndarray | list[float],
        test_signal: np.ndarray | list[float],
        dt: float = 0.0001,
        t_start_s: Optional[float] = None,
        t_end_s: Optional[float] = None
    ) -> Dict[str, float | bool | str]:
        """
        Calculates Sprague & Geers Comprehensive Error (SG_M, SG_P, SG_C) per FAA AC 20-146A.
        m(t): Reference Test / Measured signal
        c(t): Simulation / Calculated signal
        """
        c = np.asarray(sim_signal, dtype=np.float64)
        m = np.asarray(test_signal, dtype=np.float64)

        n = min(len(c), len(m))
        if n < 5:
            return {
                "sg_magnitude_m": 1.0,
                "sg_phase_p": 1.0,
                "sg_comprehensive_c": 1.414,
                "peak_diff_pct": 100.0,
                "is_faa_compliant": False,
                "status": "INSUFFICIENT_SAMPLES"
            }

        c = c[:n]
        m = m[:n]

        # Time window slicing
        idx_start = 0 if t_start_s is None else max(0, int(t_start_s / dt))
        idx_end = n if t_end_s is None else min(n, int(t_end_s / dt))
        if idx_end <= idx_start + 2:
            idx_start, idx_end = 0, n

        c_win = c[idx_start:idx_end]
        m_win = m[idx_start:idx_end]
        win_duration = max(1e-6, (idx_end - idx_start) * dt)

        # 1. Integrals Imm, Icc, Imc
        i_mm = cls._integrate_trapezoid(m_win ** 2, dt) / win_duration
        i_cc = cls._integrate_trapezoid(c_win ** 2, dt) / win_duration
        i_mc = cls._integrate_trapezoid(m_win * c_win, dt) / win_duration

        if i_mm <= 1e-9 or i_cc <= 1e-9:
            return {
                "sg_magnitude_m": 0.0 if (i_mm <= 1e-9 and i_cc <= 1e-9) else 1.0,
                "sg_phase_p": 0.0,
                "sg_comprehensive_c": 0.0 if (i_mm <= 1e-9 and i_cc <= 1e-9) else 1.0,
                "peak_diff_pct": 0.0,
                "is_faa_compliant": True if (i_mm <= 1e-9 and i_cc <= 1e-9) else False,
                "status": "ZERO_ENERGY_SIGNAL"
            }

        # 2. Magnitude Error (SG_M)
        sg_m = float(np.sqrt(i_cc / i_mm) - 1.0)

        # 3. Phase Error (SG_P)
        cos_theta = np.clip(i_mc / np.sqrt(i_mm * i_cc), -1.0, 1.0)
        sg_p = float((1.0 / np.pi) * np.arccos(cos_theta))

        # 4. Comprehensive Error (SG_C)
        sg_c = float(np.sqrt(sg_m ** 2 + sg_p ** 2))

        # Peak difference
        m_peak = float(np.max(np.abs(m_win)))
        c_peak = float(np.max(np.abs(c_win)))
        peak_diff = abs(c_peak - m_peak) / max(1e-6, m_peak) * 100.0

        # FAA AC 20-146A Threshold: SG_C <= 0.10 (10%) and Peak Diff <= 10%
        is_compliant = bool(sg_c <= 0.10 and peak_diff <= 10.0)

        return {
            "sg_magnitude_m": round(sg_m, 4),
            "sg_phase_p": round(sg_p, 4),
            "sg_comprehensive_c": round(sg_c, 4),
            "peak_diff_pct": round(peak_diff, 2),
            "is_faa_compliant": is_compliant,
            "status": "FAA_AC20_146A_COMPLIANT" if is_compliant else "FAA_DEVIATION_EXCEEDS_10PCT"
        }

class Iso18571CorrelationEngine:
    """
    ISO/TS 18571 Objective Curve Comparison and Biomechanical Validation Engine.
    Evaluates simulation waveforms against experimental crash sled test signals.
    """

    def __init__(self, weights: Optional[IsoTs18571Weights] = None, dt: float = 0.0001):
        self.weights = weights or IsoTs18571Weights()
        self.dt = dt

    @staticmethod
    def _integrate_trapezoid(arr: np.ndarray, dt: float) -> float:
        return FAA_AC20_146A_CorrelationEngine._integrate_trapezoid(arr, dt)

    def evaluate_curve_correlation(
        self,
        sim_signal: np.ndarray | list[float],
        ref_signal: np.ndarray | list[float],
        a0_inner: float = 0.05,
        b0_outer: float = 0.50,
        tau_max_pct: float = 0.20
    ) -> Dict[str, float | str]:
        """
        Calculates full ISO/TS 18571 rating R in [0.0, 1.0] (1.0 = perfect match).
        """
        s = np.asarray(sim_signal, dtype=np.float64)
        t = np.asarray(ref_signal, dtype=np.float64)

        n = min(len(s), len(t))
        if n < 10 or np.all(t == 0):
            return {
                "overall_iso_rating": 0.0,
                "corridor_rating_z": 0.0,
                "phase_rating_ep": 0.0,
                "magnitude_rating_em": 0.0,
                "slope_rating_es": 0.0,
                "status": "INSUFFICIENT_DATA"
            }

        s = s[:n]
        t = t[:n]

        # 1. Corridor Rating (Z)
        t_norm = max(1e-6, float(np.max(np.abs(t))))
        diff = np.abs(s - t)
        inner_limit = a0_inner * t_norm
        outer_limit = b0_outer * t_norm

        z_t = np.zeros(n, dtype=np.float64)
        for i in range(n):
            d = diff[i]
            if d <= inner_limit:
                z_t[i] = 1.0
            elif d >= outer_limit:
                z_t[i] = 0.0
            else:
                z_t[i] = (1.0 - (d - inner_limit) / max(1e-6, outer_limit - inner_limit)) ** 2

        z_score = float(np.mean(z_t))

        # 2. Phase Rating (E_P) via cross-correlation
        s_centered = s - np.mean(s)
        t_centered = t - np.mean(t)
        norm_factor = np.sqrt(np.sum(s_centered**2) * np.sum(t_centered**2))
        
        if norm_factor > 1e-9:
            cross_corr = np.correlate(s_centered, t_centered, mode='full')
            lags = np.arange(-n + 1, n)
            best_lag_idx = int(np.argmax(cross_corr))
            tau_star = abs(lags[best_lag_idx]) * self.dt
        else:
            tau_star = 0.0

        total_duration = n * self.dt
        tau_max = max(1e-6, total_duration * tau_max_pct)
        ep_score = float(max(0.0, 1.0 - (tau_star / tau_max)))

        # 3. Magnitude Rating (E_M)
        area_s = self._integrate_trapezoid(s, self.dt)
        area_t = self._integrate_trapezoid(t, self.dt)
        denom_area = max(1e-6, self._integrate_trapezoid(np.abs(t), self.dt))
        em_score = float(max(0.0, 1.0 - abs(area_s - area_t) / denom_area))

        # 4. Slope / Shape Rating (E_S) via derivative correlation
        ds = np.gradient(s, self.dt)
        dt_sig = np.gradient(t, self.dt)
        ds_mean = np.mean(ds)
        dt_mean = np.mean(dt_sig)

        num_cov = np.sum((ds - ds_mean) * (dt_sig - dt_mean))
        denom_cov = np.sqrt(np.sum((ds - ds_mean)**2) * np.sum((dt_sig - dt_mean)**2))
        es_score = float(max(0.0, num_cov / max(1e-9, denom_cov))) if denom_cov > 1e-9 else 0.0

        # Composite ISO Score
        w = self.weights
        r_composite = (
            w.w_corridor * z_score +
            w.w_phase * ep_score +
            w.w_magnitude * em_score +
            w.w_slope * es_score
        )

        return {
            "overall_iso_rating": round(float(r_composite), 3),
            "corridor_rating_z": round(z_score, 3),
            "phase_rating_ep": round(ep_score, 3),
            "magnitude_rating_em": round(em_score, 3),
            "slope_rating_es": round(es_score, 3),
            "status": "EXCELLENT_CORRELATION" if r_composite >= 0.85 else ("ACCEPTABLE" if r_composite >= 0.70 else "MARGINAL")
        }
