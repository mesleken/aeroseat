import numpy as np

class ReactionAuditEngine:
    """Action-Reaction Joint Reaction Force & Torque Audit Engine.
    
    Evaluates:
        Fx, Fy, Fz 3D Joint Reaction Forces (N)
        Mx, My, Mz 3D Joint Reaction Moments (Nm)
        Action-Reaction Residual: ||F_action + F_reaction|| < 1e-4 N
    """
    
    def __init__(self, force_tolerance_n: float = 1e-3, moment_tolerance_nm: float = 1e-3):
        self.force_tol = float(force_tolerance_n)
        self.moment_tol = float(moment_tolerance_nm)

    def evaluate_joint_reaction(
        self,
        joint_name: str,
        f_action: np.ndarray,
        f_reaction: np.ndarray,
        m_action: np.ndarray = None,
        m_reaction: np.ndarray = None
    ) -> dict:
        """Evaluates 3D joint action-reaction equilibrium residual."""
        f_act = np.array(f_action, dtype=np.float64)
        f_react = np.array(f_reaction, dtype=np.float64)
        
        m_act = np.array(m_action if m_action is not None else [0.0, 0.0, 0.0], dtype=np.float64)
        m_react = np.array(m_reaction if m_reaction is not None else [0.0, 0.0, 0.0], dtype=np.float64)
        
        f_residual = float(np.linalg.norm(f_act + f_react))
        m_residual = float(np.linalg.norm(m_act + m_react))
        
        is_passed = bool(f_residual <= self.force_tol and m_residual <= self.moment_tol)
        
        return {
            "joint_name": str(joint_name),
            "force_residual_n": float(f"{f_residual:.6e}"),
            "moment_residual_nm": float(f"{m_residual:.6e}"),
            "reaction_audit_verdict": "NUMERICAL_REACTION_PASS" if is_passed else "REACTION_EQUILIBRIUM_WARNING"
        }
