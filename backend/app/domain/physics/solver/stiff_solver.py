import numpy as np

class AdaptiveTimestepSolver:
    """Stiff System Adaptive Timestep Controller & Event-Driven Integrator.
    
    Dynamically adjusts time step dt based on local truncation error estimates:
        e_local = ||x_high_order - x_low_order||
        dt_new = dt * min(2.0, max(0.2, 0.9 * (tol / e_local)^0.2))
    """
    
    def __init__(
        self,
        dt_min_s: float = 1e-6,
        dt_max_s: float = 1e-3,
        error_tolerance: float = 1e-4
    ):
        self.dt_min = float(dt_min_s)
        self.dt_max = float(dt_max_s)
        self.tol = float(error_tolerance)

    def compute_next_timestep(self, current_dt: float, local_error_norm: float) -> float:
        """Computes optimal next time step dt based on truncation error norm."""
        err = max(1e-9, float(local_error_norm))
        ratio = (self.tol / err) ** 0.20
        scale = float(min(2.0, max(0.2, 0.90 * ratio)))
        
        new_dt = current_dt * scale
        return float(min(self.dt_max, max(self.dt_min, new_dt)))

class EventDetector:
    """Discrete Impact Event & State Transition Detector (g(q) = 0)."""
    
    @staticmethod
    def detect_event_crossing(g_prev: float, g_curr: float) -> bool:
        """Returns True if state boundary condition g(q) = 0 was crossed during step."""
        return bool(g_prev * g_curr <= 0.0 and g_prev != g_curr)
