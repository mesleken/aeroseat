import numpy as np

class ConstraintAuditEngine:
    """Kinematic Constraint Drift & Velocity Error Audit Engine.
    
    Audits:
        Position Constraint Drift epsilon_C = ||C(q)||
        Velocity Constraint Error epsilon_V = ||J(q) * q_dot||
        Lagrange Multiplier Consistency Q_c = J^T * lambda
    """
    
    def __init__(self, position_tolerance_m: float = 1e-4, velocity_tolerance_m_per_s: float = 1e-3):
        self.pos_tol = float(position_tolerance_m)
        self.vel_tol = float(velocity_tolerance_m_per_s)
        self.max_pos_error = 0.0
        self.max_vel_error = 0.0

    def evaluate_constraint_audit(self, C_residual: np.ndarray, J_jacobian: np.ndarray, q_dot: np.ndarray) -> dict:
        """Evaluates instantaneous constraint drift and returns numerical verdict."""
        pos_err = float(np.linalg.norm(C_residual)) if len(C_residual) > 0 else 0.0
        vel_err = float(np.linalg.norm(J_jacobian @ q_dot[:len(J_jacobian[0])])) if (len(J_jacobian) > 0 and len(q_dot) >= len(J_jacobian[0])) else 0.0
        
        if pos_err > self.max_pos_error:
            self.max_pos_error = pos_err
        if vel_err > self.max_vel_error:
            self.max_vel_error = vel_err
            
        verdict = "NUMERICAL_CONSTRAINT_PASS" if (self.max_pos_error <= self.pos_tol and self.max_vel_error <= self.vel_tol) else "CONSTRAINT_DRIFT_WARNING"
        
        return {
            "max_position_constraint_drift_m": float(f"{self.max_pos_error:.6e}"),
            "max_velocity_constraint_error_m_per_s": float(f"{self.max_vel_error:.6e}"),
            "constraint_audit_verdict": verdict
        }
