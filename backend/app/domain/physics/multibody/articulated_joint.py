import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class ArticulatedJointConfig:
    """Anatomical parameter definition for modular multi-body dummy joints."""
    name: str
    k_rot: float           # N*m/rad
    c_rot: float           # N*m*s/rad
    n_exp: float = 1.5     # Non-linear Hunt-Crossley exponent
    limit_min_rad: float = -np.pi / 2.0
    limit_max_rad: float = np.pi / 2.0
    stop_k: float = 85000.0 # N*m/rad (anatomical joint limit stop stiffness)
    stop_c: float = 2500.0  # N*m*s/rad

class ArticulatedJoint:
    """
    Modular Reduced-Coordinate Articulated Joint for Hybrid III Multi-Body Kinematic Chains.
    Implements Hunt-Crossley non-linear viscoelastic stiffness and anatomical end-stop limits.
    """

    def __init__(self, config: ArticulatedJointConfig):
        self.cfg = config

    def compute_restoring_moment(self, angle_rad: float, omega_rad_per_s: float) -> tuple[float, bool]:
        """
        Calculates joint resisting moment (N*m) and returns (moment_nm, is_limit_exceeded).
        """
        theta = float(angle_rad)
        omega = float(omega_rad_per_s)
        
        abs_theta = abs(theta)
        sign = 1.0 if theta >= 0 else -1.0
        
        # 1. Hunt-Crossley nominal joint resistance
        d_n = (abs_theta ** self.cfg.n_exp) if abs_theta > 0 else 0.0
        m_nominal = self.cfg.k_rot * d_n * sign + self.cfg.c_rot * d_n * omega

        # 2. Anatomical Limit Stop Check
        is_exceeded = False
        m_stop = 0.0

        if theta < self.cfg.limit_min_rad:
            is_exceeded = True
            delta_stop = self.cfg.limit_min_rad - theta
            m_stop = -(self.cfg.stop_k * delta_stop + self.cfg.stop_c * max(0.0, -omega))
        elif theta > self.cfg.limit_max_rad:
            is_exceeded = True
            delta_stop = theta - self.cfg.limit_max_rad
            m_stop = self.cfg.stop_k * delta_stop + self.cfg.stop_c * max(0.0, omega)

        total_moment = m_nominal + m_stop
        return float(total_moment), is_exceeded
