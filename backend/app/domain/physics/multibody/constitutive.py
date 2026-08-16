import numpy as np

class ConstitutiveModels:
    """
    High-Fidelity Constitutive Models for Crash Dynamics.
    Replaces simple linear springs with advanced nonlinear and plastic mechanics.
    """
    
    @staticmethod
    def bilinear_elastoplastic(displacement, velocity, current_plastic_strain, k_elastic, k_plastic, yield_force):
        """
        Bilinear Elasto-Plastic model for metallic seat structures (e.g., aluminum legs).
        Tracks plastic deformation (permanent set) and absorbs energy realistically.
        Returns: force, new_plastic_strain
        """
        # Effective elastic displacement relative to plastic set
        x_eff = displacement - current_plastic_strain
        
        # Trial elastic force
        f_trial = k_elastic * x_eff
        
        if abs(f_trial) <= yield_force:
            # Pure elastic domain
            return f_trial, current_plastic_strain
        else:
            # Yielding / Plastic domain
            sign = np.sign(f_trial)
            f_yield = sign * yield_force
            # Force increases with plastic stiffness (strain hardening)
            # The additional displacement beyond yield
            x_yield = sign * (yield_force / k_elastic)
            x_excess = x_eff - x_yield
            
            f_plastic = f_yield + k_plastic * x_excess
            
            # Update permanent plastic strain for the next timestep
            new_plastic_strain = current_plastic_strain + x_excess * (1.0 - k_plastic/k_elastic)
            
            # Add dynamic strain rate effect (damping)
            f_dynamic = f_plastic + (500.0 * velocity if sign == np.sign(velocity) else 0)
            
            return f_dynamic, new_plastic_strain

    @staticmethod
    def nonlinear_belt_webbing(strain, strain_rate, k1, k2, k3, c):
        """
        Nonlinear polynomial stress-strain curve typical of Nylon/Polyester seatbelts.
        Belts stiffen drastically as they stretch.
        """
        if strain <= 0:
            return 0.0
        
        # Nonlinear stiffness
        f_static = k1 * strain + k2 * (strain**2) + k3 * (strain**3)
        
        # Viscoelastic damping (only during extension)
        f_damping = c * strain_rate if strain_rate > 0 else c * 0.1 * strain_rate
        
        f_total = max(0.0, f_static + f_damping)
        return f_total
        
    @staticmethod
    def cushion_hysteresis(penetration, velocity, k, c, yield_pen, unloading_factor=0.3):
        """
        Foam cushion loading/unloading hysteresis.
        Foams load stiffly but unload softly, dissipating energy.
        """
        if penetration <= 0:
            return 0.0
            
        if velocity >= 0:
            # Loading: stiffer
            force = k * penetration + c * velocity
            # Bottoming out effect (exponential stiffness increase)
            if penetration > yield_pen:
                force += (k * 2.0) * ((penetration - yield_pen)**2)
        else:
            # Unloading: softer, hysteretic loss
            force = (k * unloading_factor) * penetration + c * velocity
            
        return max(0.0, force)
