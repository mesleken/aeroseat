import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

@dataclass
class HICResult:
    """Head Injury Criterion calculation result."""
    hic_value: float
    t1_s: float
    t2_s: float
    window_duration_ms: float
    is_compliant: bool
    status: str

@dataclass
class InjuryAssessmentSummary:
    """Full FAA 14 CFR § 25.562 / EASA CS-25 Injury Assessment."""
    hic15: float
    hic36: float
    hic_compliant: bool
    lumbar_load_n: float
    lumbar_load_lbs: float
    lumbar_compliant: bool
    femur_load_left_n: float
    femur_load_right_n: float
    femur_compliant: bool
    nij_max: float
    nij_compliant: bool
    overall_certification_pass: bool

class AeroSeatBiomechanics:
    """
    AeroSeat - Core Biomechanics & Injury Prediction Solver.
    Calculates Head Injury Criterion (HIC) via sliding-window search,
    lumbar spinal compression, femur axial loads, and neck injury criteria (Nij).
    """

    @staticmethod
    def _integrate_trapezoid(arr: np.ndarray, time_arr: np.ndarray) -> float:
        if len(arr) < 2:
            return 0.0
        if hasattr(np, 'trapezoid'):
            return float(np.trapezoid(arr, time_arr))
        elif hasattr(np, 'trapz'):
            return float(np.trapz(arr, time_arr))
        dt = np.mean(np.diff(time_arr))
        return float(np.sum(0.5 * (arr[:-1] + arr[1:]) * dt))

    def calculate_hic(
        self,
        time_s: np.ndarray | list[float],
        accel_g: np.ndarray | list[float],
        max_window_s: float = 0.015,
        hic_limit: float = 1000.0
    ) -> HICResult:
        """
        Calculates maximum Head Injury Criterion (HIC) via analytical sliding window optimization.
        
        Formula:
            HIC = max_{t1, t2} { (t2 - t1) * [ (1 / (t2 - t1)) * int_{t1}^{t2} a(t) dt ]^2.5 }
            subject to (t2 - t1) <= max_window_s
        """
        t = np.asarray(time_s, dtype=np.float64)
        a = np.asarray(accel_g, dtype=np.float64)

        n = len(t)
        if n < 5 or np.all(a == 0):
            return HICResult(
                hic_value=0.0,
                t1_s=0.0,
                t2_s=0.0,
                window_duration_ms=0.0,
                is_compliant=True,
                status="NO_ACCELERATION_DETECTED"
            )

        # Cumulative trapezoidal integral for fast O(N) or O(N^2) evaluation
        cum_a = np.zeros(n, dtype=np.float64)
        for k in range(1, n):
            dt_k = t[k] - t[k - 1]
            cum_a[k] = cum_a[k - 1] + 0.5 * (a[k] + a[k - 1]) * dt_k

        max_hic = 0.0
        best_t1 = float(t[0])
        best_t2 = float(t[0])

        for i in range(n):
            for j in range(i + 1, n):
                dt = t[j] - t[i]
                if dt > max_window_s:
                    break
                if dt < 1e-4:
                    continue

                int_a = cum_a[j] - cum_a[i]
                avg_a = int_a / dt
                if avg_a <= 0.0:
                    continue

                hic_cand = dt * (avg_a ** 2.5)
                if hic_cand > max_hic:
                    max_hic = hic_cand
                    best_t1 = float(t[i])
                    best_t2 = float(t[j])

        window_ms = (best_t2 - best_t1) * 1000.0
        is_compliant = bool(max_hic <= hic_limit)

        return HICResult(
            hic_value=round(float(max_hic), 2),
            t1_s=round(best_t1, 5),
            t2_s=round(best_t2, 5),
            window_duration_ms=round(window_ms, 2),
            is_compliant=is_compliant,
            status="PASS" if is_compliant else "FAIL_HIC_LIMIT_EXCEEDED"
        )

    def evaluate_full_injury_criteria(
        self,
        time_s: np.ndarray | list[float],
        head_accel_g: np.ndarray | list[float],
        lumbar_force_n: np.ndarray | list[float],
        femur_left_n: np.ndarray | list[float],
        femur_right_n: np.ndarray | list[float],
        neck_fz_n: Optional[np.ndarray | list[float]] = None,
        neck_my_nm: Optional[np.ndarray | list[float]] = None,
        dummy_type: str = "FAA_HIII_50M"
    ) -> InjuryAssessmentSummary:
        """
        Evaluates full FAA 14 CFR § 25.562 / EASA CS-25 injury criteria suite.
        - HIC15 <= 1000
        - Lumbar Load <= 1500 lbs (6672 N)
        - Femur Loads <= 2250 lbs (10008 N)
        - Nij <= 1.0
        """
        t = np.asarray(time_s, dtype=np.float64)
        a_head = np.asarray(head_accel_g, dtype=np.float64)

        # 1. HIC15 and HIC36
        hic15_res = self.calculate_hic(t, a_head, max_window_s=0.015)
        hic36_res = self.calculate_hic(t, a_head, max_window_s=0.036)

        # 2. Lumbar Load (FAA Limit: 1500 lbs = 6672.33 N)
        f_lumbar = np.asarray(lumbar_force_n, dtype=np.float64)
        peak_lumbar_n = float(np.max(np.abs(f_lumbar))) if len(f_lumbar) > 0 else 0.0
        peak_lumbar_lbs = peak_lumbar_n * 0.224809
        lumbar_pass = peak_lumbar_lbs <= 1500.0

        # 3. Femur Loads (FAA Limit: 2250 lbs = 10008.5 N)
        f_fl = np.asarray(femur_left_n, dtype=np.float64)
        f_fr = np.asarray(femur_right_n, dtype=np.float64)
        peak_femur_l = float(np.max(np.abs(f_fl))) if len(f_fl) > 0 else 0.0
        peak_femur_r = float(np.max(np.abs(f_fr))) if len(f_fr) > 0 else 0.0
        femur_pass = (peak_femur_l <= 10008.5) and (peak_femur_r <= 10008.5)

        # 4. Neck Nij (FAA Limit: Nij <= 1.0)
        nij_max = 0.0
        if neck_fz_n is not None and neck_my_nm is not None:
            from app.domain.injury_metrics import calculate_nij
            nij_series = calculate_nij(neck_fz_n, neck_my_nm, dummy_type=dummy_type)
            if len(nij_series) > 0:
                nij_max = float(np.max(nij_series))
        nij_pass = nij_max <= 1.0

        overall_pass = bool(hic15_res.is_compliant and lumbar_pass and femur_pass and nij_pass)

        return InjuryAssessmentSummary(
            hic15=hic15_res.hic_value,
            hic36=hic36_res.hic_value,
            hic_compliant=hic15_res.is_compliant,
            lumbar_load_n=round(peak_lumbar_n, 2),
            lumbar_load_lbs=round(peak_lumbar_lbs, 2),
            lumbar_compliant=lumbar_pass,
            femur_load_left_n=round(peak_femur_l, 2),
            femur_load_right_n=round(peak_femur_r, 2),
            femur_compliant=femur_pass,
            nij_max=round(nij_max, 3),
            nij_compliant=nij_pass,
            overall_certification_pass=overall_pass
        )
