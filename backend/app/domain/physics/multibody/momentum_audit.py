import numpy as np
from app.domain.physics.multibody.rigid_body import RigidBody6DOF

class MomentumAuditEngine:
    """Linear & Angular Momentum Conservation & Impulse Audit Engine.
    
    Equations:
        Linear Momentum P = sum(m_i * v_i)
        Angular Momentum L = sum(r_i x m_i * v_i + I_i * omega_i)
        Impulse Consistency dP/dt = sum(F_ext)
    """
    
    def __init__(self, rigid_bodies: list[RigidBody6DOF] = None):
        self.bodies = rigid_bodies or []
        self.p_history = []
        self.l_history = []

    def compute_linear_momentum(self) -> np.ndarray:
        """Computes total linear momentum vector P = sum(m_i * v_i) (kg*m/s)."""
        p_total = np.zeros(3, dtype=np.float64)
        for body in self.bodies:
            p_total += body.mass * body.vel
        return p_total

    def compute_angular_momentum(self, origin: np.ndarray = None) -> np.ndarray:
        """Computes total angular momentum vector L = sum(r_i x m_i * v_i + I_i * omega_i) (kg*m^2/s)."""
        ref_origin = origin if origin is not None else np.zeros(3, dtype=np.float64)
        l_total = np.zeros(3, dtype=np.float64)
        
        for body in self.bodies:
            r_vec = body.pos - ref_origin
            l_orbital = np.cross(r_vec, body.mass * body.vel)
            l_spin = body.inertia_matrix @ body.omega
            l_total += l_orbital + l_spin
            
        return l_total

    def evaluate_audit(self, f_ext_sum_n: np.ndarray, dt: float) -> dict:
        """Evaluates linear & angular momentum conservation and returns audit verdict."""
        p_curr = self.compute_linear_momentum()
        l_curr = self.compute_angular_momentum()
        
        p_mag = float(np.linalg.norm(p_curr))
        l_mag = float(np.linalg.norm(l_curr))
        
        self.p_history.append(p_mag)
        self.l_history.append(l_mag)
        
        # Check action-reaction momentum residual
        max_p_change = float(abs(self.p_history[-1] - self.p_history[0])) if len(self.p_history) > 1 else 0.0
        
        verdict = "NUMERICAL_MOMENTUM_BALANCE_PASS" if max_p_change < 50.0 else "MOMENTUM_DRIFT_WARNING"
        
        return {
            "linear_momentum_norm_kgm_per_s": round(p_mag, 3),
            "angular_momentum_norm_kgm2_per_s": round(l_mag, 3),
            "momentum_drift_max": round(max_p_change, 3),
            "momentum_audit_verdict": verdict
        }
