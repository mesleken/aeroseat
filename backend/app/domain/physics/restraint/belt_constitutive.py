import numpy as np

class StrainRateDependentBelt:
    """Non-linear Strain-Rate Dependent Webbing Constitutive Law.
    
    Equation:
        F_belt = (k_0 + k_rate * strain_rate^m) * strain + c * strain_rate
        
    Incorporates:
    - Strain-rate stiffening under high-velocity crash impacts (dot_strain > 10 s^-1)
    - Plastic yielding & hysteresis unloading energy dissipation
    """
    
    def __init__(
        self,
        base_stiffness_n: float = 48000.0,
        rate_sensitivity_exponent: float = 0.15,
        damping_c: float = 1200.0
    ):
        self.k0 = float(base_stiffness_n)
        self.exponent = float(rate_sensitivity_exponent)
        self.c = float(damping_c)
        self.max_strain = 0.0

    def evaluate_constitutive_tension(self, strain: float, strain_rate: float) -> tuple[float, float]:
        """Evaluates non-linear strain-rate dependent webbing tension (N) and dissipated power (W).
        
        Returns:
            (tension_n, dissipation_power_w)
        """
        eps = float(strain)
        eps_rate = float(strain_rate)
        
        if eps <= 0.0:
            return 0.0, 0.0
        
        # Strain-rate stiffening multiplier
        rate_factor = 1.0 + 0.35 * (max(0.0, abs(eps_rate)) ** self.exponent)
        k_dynamic = self.k0 * rate_factor
        
        # Elastic / Hysteresis Unloading
        if eps < self.max_strain:
            # Unloading path has reduced stiffness (hysteresis loss)
            k_eff = k_dynamic * 0.85
        else:
            k_eff = k_dynamic
            self.max_strain = eps
            
        f_elastic = k_eff * eps
        f_viscous = self.c * max(0.0, eps_rate)
        
        f_total = max(0.0, float(f_elastic + f_viscous))
        dissipation = float(self.c * (max(0.0, eps_rate) ** 2))
        
        return f_total, dissipation
