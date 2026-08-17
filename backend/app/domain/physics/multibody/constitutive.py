import numpy as np

class ConstitutiveModels:
    """
    High-Fidelity Constitutive Models for Crash Dynamics (Phase 12 Industrial Solver Integration).
    Provides non-linear elastoplasticity, 3-phase cellular foam hysteresis,
    LS-DYNA SOFT=1 automatic mass/dt contact stiffness, Courant critical timestep calculation,
    and Hunt-Crossley viscoelastic joint contact mechanics.
    """
    
    @staticmethod
    def compute_soft1_contact_stiffness(
        m1_kg: float,
        m2_kg: float,
        dt_s: float,
        sofscl: float = 0.10
    ) -> float:
        """
        LS-DYNA SOFT=1 Mass / Timestep-Based Contact Stiffness Formulation.
        k_c = SOFSCL * m_eff / (dt^2)
        Eliminates numerical instability and calibration sensitivity in dissimilar body contact.
        """
        m1 = max(0.1, float(m1_kg))
        m2 = max(0.1, float(m2_kg))
        dt = max(1e-6, float(dt_s))
        m_eff = (m1 * m2) / (m1 + m2)
        return float(sofscl * (m_eff / (dt ** 2)))

    @staticmethod
    def compute_critical_timestep(
        m_eff_kg: float,
        k_eff_n_per_m: float,
        tssfac: float = 0.70
    ) -> float:
        """
        OpenRadioss / Courant-Friedrichs-Lewy (CFL) Critical Timestep Calculation.
        dt_crit = TSSFAC * 2 * sqrt(m_eff / k_eff)
        """
        m = max(1e-4, float(m_eff_kg))
        k = max(1.0, float(k_eff_n_per_m))
        omega_n = np.sqrt(k / m)
        dt_crit = tssfac * (2.0 / omega_n)
        return float(dt_crit)

    @staticmethod
    def bilinear_elastoplastic(
        displacement: float,
        velocity: float,
        current_plastic_strain: float,
        k_elastic: float,
        k_plastic: float,
        yield_force: float,
        damping_c: float = 1200.0
    ) -> tuple[float, float]:
        """
        Bilinear Elasto-Plastic model for metallic seat structures and mounting tracks.
        Tracks permanent plastic deformation and dissipates kinematic energy realistically.
        Returns: (force_n, new_plastic_strain_m)
        """
        x_eff = displacement - current_plastic_strain
        f_trial = k_elastic * x_eff
        
        if abs(f_trial) <= yield_force:
            f_elastic = f_trial + damping_c * velocity
            return f_elastic, current_plastic_strain
        else:
            sign = 1.0 if f_trial > 0 else -1.0
            f_yield = sign * yield_force
            x_yield = sign * (yield_force / max(1.0, k_elastic))
            x_excess = x_eff - x_yield
            
            f_plastic = f_yield + k_plastic * x_excess
            plastic_ratio = max(0.0, min(1.0, 1.0 - (k_plastic / max(1.0, k_elastic))))
            new_plastic_strain = current_plastic_strain + x_excess * plastic_ratio
            f_dynamic = f_plastic + damping_c * 0.5 * velocity
            
            return f_dynamic, new_plastic_strain

    @staticmethod
    def nonlinear_belt_webbing(
        extension_m: float,
        velocity_mps: float,
        k_base: float,
        k_quad: float = 0.0,
        k_cube: float = 0.0,
        c_viscous: float = 1500.0,
        ref_length_m: float = 0.50,
        slack_m: float = 0.0
    ) -> float:
        """
        Nonlinear polynomial stress-strain curve typical of aviation Polyester/Nylon restraints.
        Webbing transitions from initial slack take-up to linear elasticity, and sharply
        stiffens (progressive lockup) under high tensile elongation.
        Includes strain-rate dynamic amplification factor (DAF).
        """
        eff_ext = extension_m - slack_m
        if eff_ext <= 0.0:
            return 0.0
        
        strain = eff_ext / max(0.10, ref_length_m)
        strain_rate = velocity_mps / max(0.10, ref_length_m)
        
        if k_quad == 0.0 and k_cube == 0.0:
            f_static = k_base * eff_ext * (1.0 + 8.0 * strain + 45.0 * (strain ** 2))
        else:
            f_static = k_base * eff_ext + k_quad * (eff_ext ** 2) + k_cube * (eff_ext ** 3)
            
        rate_factor = 1.0 + 0.08 * np.log1p(max(0.0, strain_rate * 10.0))
        damping = (c_viscous * velocity_mps) if velocity_mps > 0 else (c_viscous * 0.15 * velocity_mps)
        
        f_total = max(0.0, f_static * rate_factor + damping)
        return float(f_total)

    @staticmethod
    def resolve_belt_force_3d(
        tension_n: float,
        body_pos_xyz: tuple[float, float, float] | np.ndarray,
        anchor_pos_xyz: tuple[float, float, float] | np.ndarray
    ) -> tuple[float, float, float]:
        """
        Resolves 1D restraint tensile magnitude into a 3D Cartesian force vector [Fx, Fy, Fz].
        Vector pulls body towards the anchor point along the line of action.
        """
        if tension_n <= 0.0:
            return (0.0, 0.0, 0.0)
            
        r_vec = np.array(anchor_pos_xyz, dtype=np.float64) - np.array(body_pos_xyz, dtype=np.float64)
        dist = np.linalg.norm(r_vec)
        if dist < 1e-6:
            return (tension_n, 0.0, 0.0)
            
        unit_vec = r_vec / dist
        f_3d = tension_n * unit_vec
        return (float(f_3d[0]), float(f_3d[1]), float(f_3d[2]))

    @staticmethod
    def hunt_crossley_joint(
        delta_m: float,
        velocity_mps: float,
        k_joint: float,
        c_joint: float,
        exponent: float = 1.5
    ) -> float:
        """
        Hunt-Crossley Non-Linear Viscoelastic Inter-Segment Joint Model.
        F = k * delta^n + c * delta^n * v
        Provides smooth non-linear stiffness and zero damping discontinuity at impact boundaries.
        """
        if abs(delta_m) <= 0.0:
            return 0.0
            
        sign = 1.0 if delta_m >= 0 else -1.0
        abs_delta = abs(delta_m)
        d_n = abs_delta ** exponent
        
        f_elastic = k_joint * d_n * sign
        f_damping = c_joint * d_n * velocity_mps
        
        return float(f_elastic + f_damping)

    @staticmethod
    def cushion_3phase_foam(
        penetration_m: float,
        velocity_mps: float,
        k_cushion: float,
        c_cushion: float,
        plateau_start_m: float = 0.025,
        densification_start_m: float = 0.065,
        plateau_factor: float = 0.35,
        densification_k: float = 3.5,
        unloading_factor: float = 0.25
    ) -> float:
        """
        3-Phase Open-Cell Polyurethane Foam Cushion Constitutive Model.
        Phase 1: Linear elastic cell wall bending (0 to plateau_start).
        Phase 2: Plateau elastic cell buckling / collapse with near-constant stress.
        Phase 3: Densification / bottoming out where crushed cell walls contact (exponential stiffening).
        Features continuous hysteretic energy absorption during rebound unloading.
        """
        if penetration_m <= 0.0:
            return 0.0
            
        # 1. Loading curve calculation
        if penetration_m <= plateau_start_m:
            f_load = k_cushion * penetration_m
        elif penetration_m <= densification_start_m:
            f_at_plateau = k_cushion * plateau_start_m
            excess = penetration_m - plateau_start_m
            f_load = f_at_plateau + (k_cushion * plateau_factor) * excess
        else:
            f_at_plateau = k_cushion * plateau_start_m
            plateau_span = densification_start_m - plateau_start_m
            f_at_dens = f_at_plateau + (k_cushion * plateau_factor) * plateau_span
            excess_dens = penetration_m - densification_start_m
            f_load = f_at_dens + (k_cushion * densification_k) * excess_dens + (k_cushion * 18.0) * (excess_dens ** 2)
            
        # 2. Hysteretic Unloading & Viscoelasticity
        v_norm = np.tanh(velocity_mps / 0.08)
        scale = 0.5 * (1.0 + unloading_factor) + 0.5 * (1.0 - unloading_factor) * v_norm
        f_elastic = f_load * scale
        f_viscous = c_cushion * velocity_mps if velocity_mps > 0 else (c_cushion * 0.20 * velocity_mps)
        
        f_total = max(0.0, f_elastic + f_viscous)
        return float(f_total)

    @staticmethod
    def cushion_hysteresis(
        penetration: float,
        velocity: float,
        k: float,
        c: float,
        yield_pen: float = 0.065,
        unloading_factor: float = 0.25
    ) -> float:
        """
        Backwards-compatible wrapper calling the high-fidelity 3-phase cellular foam model.
        """
        return ConstitutiveModels.cushion_3phase_foam(
            penetration_m=penetration,
            velocity_mps=velocity,
            k_cushion=k,
            c_cushion=c,
            plateau_start_m=0.025,
            densification_start_m=yield_pen,
            unloading_factor=unloading_factor
        )
