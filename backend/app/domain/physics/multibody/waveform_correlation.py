import numpy as np

class WaveformCorrelationEngine:
    """Waveform Time-Series Correlation & Experimental Validation Metrics Engine.
    
    Evaluates:
    - RMSE (Root Mean Square Error)
    - NRMSE (Normalized RMSE %)
    - R^2 (Coefficient of Determination)
    - Peak Error (%)
    - Time-to-Peak Error (ms)
    """
    
    @staticmethod
    def evaluate_waveform_correlation(y_sim: np.ndarray, y_exp: np.ndarray, dt: float) -> dict:
        """Computes channel-by-channel correlation metrics between simulated and experimental time series."""
        sim = np.asarray(y_sim, dtype=np.float64)
        exp = np.asarray(y_exp, dtype=np.float64)
        
        n = min(len(sim), len(exp))
        if n < 5:
            return {"status": "INSUFFICIENT_DATA"}
            
        sim_trunc = sim[:n]
        exp_trunc = exp[:n]
        
        # RMSE
        rmse = float(np.sqrt(np.mean((sim_trunc - exp_trunc) ** 2)))
        
        # NRMSE (%)
        exp_range = float(np.max(exp_trunc) - np.min(exp_trunc))
        nrmse_pct = float((rmse / exp_range * 100.0)) if exp_range > 1e-6 else 0.0
        
        # R^2 Coefficient of Determination
        ss_res = float(np.sum((exp_trunc - sim_trunc) ** 2))
        ss_tot = float(np.sum((exp_trunc - np.mean(exp_trunc)) ** 2))
        r2_score = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-6 else 1.0
        
        # Peak comparison
        peak_sim = float(np.max(np.abs(sim_trunc)))
        peak_exp = float(np.max(np.abs(exp_trunc)))
        peak_err_pct = float(abs(peak_sim - peak_exp) / max(1e-6, peak_exp) * 100.0)
        
        # Time-to-peak
        t_peak_sim = float(np.argmax(np.abs(sim_trunc)) * dt * 1000.0)
        t_peak_exp = float(np.argmax(np.abs(exp_trunc)) * dt * 1000.0)
        t_peak_err_ms = float(abs(t_peak_sim - t_peak_exp))
        
        is_validated = bool(r2_score >= 0.85 and peak_err_pct <= 10.0)
        
        return {
            "rmse": round(rmse, 4),
            "nrmse_pct": round(nrmse_pct, 2),
            "r2_score": round(r2_score, 4),
            "peak_error_pct": round(peak_err_pct, 2),
            "time_to_peak_error_ms": round(t_peak_err_ms, 2),
            "waveform_correlation_status": "EXPERIMENTAL_CORRELATION_PASS" if is_validated else "CORRELATION_PENDING"
        }
