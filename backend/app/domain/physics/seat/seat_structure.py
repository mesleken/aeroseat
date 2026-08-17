import numpy as np
from app.domain.physics.multibody.constitutive import ConstitutiveModels

class SeatStructureCompliance:
    """Seat Frame Structural Compliance, Seatback Deflection, & Persistent Yielding Engine.
    
    Models the elastoplastic pitch rotation of the seatback under occupant loading,
    tracking permanent deformation and structural compliance.
    """
    
    def __init__(
        self,
        seatback_rotational_k_nm_per_rad: float = 32000.0,
        seatback_rotational_c_nms_per_rad: float = 650.0,
        yield_torque_nm: float = 1200.0,
        inertia_kg_m2: float = 1.35
    ):
        self.k_rot = float(seatback_rotational_k_nm_per_rad)
        self.c_rot = float(seatback_rotational_c_nms_per_rad)
        self.yield_torque = float(yield_torque_nm)
        self.inertia = float(inertia_kg_m2)
        
        self.seatback_angle_rad = 0.0
        self.seatback_omega_rad_per_s = 0.0
        self.plastic_angle_rad = 0.0
        self.is_yielded = False

    def evaluate_seatback_response(
        self,
        torso_rebound_moment_nm: float = 0.0,
        dt: float = 0.001,
        applied_moment_nm: float = None
    ) -> tuple[float, float]:
        """Evaluates seatback angular deflection (rad) and restoring moment (Nm) with persistent plasticity.
        
        Returns:
            (seatback_angle_rad, restoring_moment_nm)
        """
        m_applied = float(applied_moment_nm if applied_moment_nm is not None else torso_rebound_moment_nm)
        
        # Effective elastic angle relative to accumulated plastic set
        theta_eff = self.seatback_angle_rad - self.plastic_angle_rad
        m_trial = self.k_rot * theta_eff
        
        if abs(m_trial) <= self.yield_torque:
            # Elastic regime
            m_restoring = m_trial + self.c_rot * self.seatback_omega_rad_per_s
        else:
            # Plastic yielding regime with persistent plastic deformation
            self.is_yielded = True
            sign = 1.0 if m_trial > 0 else -1.0
            m_yield = sign * self.yield_torque
            theta_yield = sign * (self.yield_torque / max(1.0, self.k_rot))
            theta_excess = theta_eff - theta_yield
            
            k_plastic = self.k_rot * 0.08  # 8% strain hardening slope
            m_plastic = m_yield + k_plastic * theta_excess
            
            # Accumulate permanent plastic angle
            self.plastic_angle_rad += theta_excess * (1.0 - k_plastic / max(1.0, self.k_rot))
            m_restoring = m_plastic + self.c_rot * 0.5 * self.seatback_omega_rad_per_s
            
        alpha = (m_applied - m_restoring) / max(0.1, self.inertia)
        
        self.seatback_omega_rad_per_s += alpha * dt
        self.seatback_angle_rad += self.seatback_omega_rad_per_s * dt
        
        return self.seatback_angle_rad, float(m_restoring)

class SeatMountingCompliance:
    """Seat-to-Sled Track Fitting & Floor Compliance Engine.
    
    Models the elastoplastic mounting of the seat to the sled floor tracks.
    """
    def __init__(
        self,
        seat_mass_kg: float = 18.0,
        mount_stiffness_n_per_m: float = 850000.0,
        mount_damping_ns_per_m: float = 18000.0,
        yield_force_n: float = 40000.0  # 40 kN plastic yield threshold
    ):
        self.m_seat = float(seat_mass_kg)
        self.k_mount = float(mount_stiffness_n_per_m)
        self.c_mount = float(mount_damping_ns_per_m)
        self.f_yield = float(yield_force_n)
        
        self.x_seat = 0.0
        self.v_seat = 0.0
        self.a_seat = 0.0
        self.is_yielded = False
        self.plastic_strain = 0.0
        
    def evaluate_seat_acceleration(
        self,
        sled_accel_m_per_s2: float,
        sled_vel_m_per_s: float,
        sled_pos_m: float,
        occupant_force_n: float,
        dt: float
    ) -> float:
        """Evaluates seat mounting dynamics and returns seat acceleration a_seat_x."""
        disp = self.x_seat - sled_pos_m
        v_rel = self.v_seat - sled_vel_m_per_s
        
        # Bilinear Elastoplastic track mounting
        f_mount, self.plastic_strain = ConstitutiveModels.bilinear_elastoplastic(
            displacement=disp,
            velocity=v_rel,
            current_plastic_strain=self.plastic_strain,
            k_elastic=self.k_mount,
            k_plastic=self.k_mount * 0.05,  # 5% plastic hardening slope
            yield_force=self.f_yield,
            damping_c=self.c_mount
        )
        
        if abs(f_mount) >= self.f_yield:
            self.is_yielded = True
            
        f_seat_net = -f_mount + occupant_force_n
        
        self.a_seat = f_seat_net / max(1.0, self.m_seat)
        self.v_seat += self.a_seat * dt
        self.x_seat += self.v_seat * dt
        
        return self.a_seat

class CushionSettlingMechanics:
    """Pre-Crash Dummy Gravity Settling & H-Point Initialization Engine."""
    @staticmethod
    def compute_initial_settling(occupant_mass_kg: float, cushion_stiffness_n_per_m: float) -> float:
        """Computes the static vertical cushion penetration (m) due to gravity."""
        g = 9.80665
        f_gravity = occupant_mass_kg * g
        settling_m = f_gravity / max(1.0, cushion_stiffness_n_per_m)
        return float(settling_m)
