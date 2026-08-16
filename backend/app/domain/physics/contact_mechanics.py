import numpy as np

class HuntCrossleyContact:
    """Hunt-Crossley Non-linear Viscoelastic Unilateral Contact Mechanics Engine.
    
    Equations:
        Fn = max(0, k * delta^n + c * (delta^n) * v_rel)
    
    Prevents unphysical adhesive tensile forces when surfaces disengage (delta -> 0).
    Includes non-linear bottoming-out stiffness for seat cushion and backrest surfaces.
    """
    
    def __init__(
        self,
        stiffness_k: float = 85000.0,
        damping_c: float = 1200.0,
        exponent_n: float = 1.5,
        bottoming_penetration_m: float = 0.035,
        bottoming_stiffness_multiplier: float = 4.5,
        friction_coeff_mu: float = 0.35
    ):
        self.k = float(stiffness_k)
        self.c = float(damping_c)
        self.n = float(exponent_n)
        self.bottoming_pen_m = float(bottoming_penetration_m)
        self.bottoming_mult = float(bottoming_stiffness_multiplier)
        self.mu = float(friction_coeff_mu)

    def evaluate_normal_force(self, penetration_m: float, penetration_velocity_m_per_s: float) -> tuple[float, float]:
        """Evaluates normal contact force Fn (N) and dynamic friction magnitude Ff (N).
        
        Returns:
            (fn_n, ff_max_n)
        """
        pen = float(penetration_m)
        v_pen = float(penetration_velocity_m_per_s)
        
        if pen <= 0.0:
            return 0.0, 0.0
        
        # Non-linear Hertzian / Hunt-Crossley elastic stiffness
        k_eff = self.k
        if pen > self.bottoming_pen_m:
            # Bottoming-out stiffness increase
            excess = pen - self.bottoming_pen_m
            k_eff += self.k * self.bottoming_mult * (excess / 0.010)**2
        
        pen_n = pen ** self.n
        fn_raw = k_eff * pen_n + self.c * pen_n * v_pen
        
        # Unilateral non-negative contact constraint
        fn = max(0.0, float(fn_raw))
        ff_max = float(self.mu * fn)
        
        return fn, ff_max

    def evaluate_tangential_friction(self, fn_n: float, sliding_velocity_m_per_s: float) -> float:
        """Evaluates continuous Coulomb-tanh sliding friction force (N)."""
        if fn_n <= 0.0:
            return 0.0
        v_slip = float(sliding_velocity_m_per_s)
        # Regularized smooth friction transition around 0.02 m/s
        return float(self.mu * fn_n * np.tanh(v_slip / 0.020))
