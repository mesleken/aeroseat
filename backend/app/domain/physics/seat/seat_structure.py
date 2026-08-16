import numpy as np

class SeatStructureCompliance:
    """Seat Frame Structural Compliance, Seatback Deflection, & Cushion Hysteresis Engine.
    
    Equations:
        I_seat * d2(theta_backrest)/dt2 + c_rot * d(theta_backrest)/dt + k_rot * theta_backrest = M_torso_rebound
    """
    
    def __init__(
        self,
        seatback_rotational_k_nm_per_rad: float = 32000.0,
        seatback_rotational_c_nms_per_rad: float = 650.0,
        yield_torque_nm: float = 1200.0
    ):
        self.k_rot = float(seatback_rotational_k_nm_per_rad)
        self.c_rot = float(seatback_rotational_c_nms_per_rad)
        self.yield_torque = float(yield_torque_nm)
        
        self.seatback_angle_rad = 0.0
        self.seatback_omega_rad_per_s = 0.0
        self.is_yielded = False

    def evaluate_seatback_response(self, torso_rebound_moment_nm: float, dt: float) -> tuple[float, float]:
        """Evaluates seatback angular deflection (rad) and restoring moment (Nm).
        
        Returns:
            (seatback_angle_rad, restoring_moment_nm)
        """
        m_applied = float(torso_rebound_moment_nm)
        
        # Check plastic yielding threshold of seatback frame
        if abs(m_applied) > self.yield_torque:
            self.is_yielded = True
            k_eff = self.k_rot * 0.15 # Post-yield reduced stiffness
        else:
            k_eff = self.k_rot
            
        m_restoring = k_eff * self.seatback_angle_rad + self.c_rot * self.seatback_omega_rad_per_s
        alpha = (m_applied - m_restoring) / 12.5 # Inertia = 12.5 kg*m^2
        
        self.seatback_omega_rad_per_s += alpha * dt
        self.seatback_angle_rad += self.seatback_omega_rad_per_s * dt
        
        return self.seatback_angle_rad, float(m_restoring)

class SeatMountingCompliance:
    """Seat-to-Sled Track Fitting & Floor Compliance Engine.
    
    Models the non-rigid mounting of the seat to the sled floor.
    Equation:
        m_seat * a_seat = F_mount + F_occupant
        F_mount = -k_mount * (x_seat - x_sled) - c_mount * (v_seat - v_sled)
    """
    def __init__(
        self,
        seat_mass_kg: float = 25.0,
        mount_stiffness_n_per_m: float = 8.5e6, # High stiffness track fitting
        mount_damping_ns_per_m: float = 15000.0,
        yield_force_n: float = 40000.0 # 40 kN plastic yield threshold
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
        
    def evaluate_seat_acceleration(self, sled_accel_m_per_s2: float, sled_vel_m_per_s: float, sled_pos_m: float, occupant_force_n: float, dt: float) -> float:
        """Evaluates seat mounting dynamics and returns seat acceleration a_seat_x."""
        from app.domain.physics.multibody.constitutive import ConstitutiveModels

        disp = self.x_seat - sled_pos_m
        v_rel = self.v_seat - sled_vel_m_per_s
        
        # Use Bilinear Elastoplastic logic
        f_mount, self.plastic_strain = ConstitutiveModels.bilinear_elastoplastic(
            displacement=disp,
            velocity=v_rel,
            current_plastic_strain=self.plastic_strain,
            k_elastic=self.k_mount,
            k_plastic=self.k_mount * 0.05,  # 5% plastic hardening slope
            yield_force=self.f_yield
        )
        
        if abs(f_mount) >= self.f_yield:
            self.is_yielded = True
            
        f_seat_net = -f_mount + occupant_force_n
        
        self.a_seat = f_seat_net / self.m_seat
        self.v_seat += self.a_seat * dt
        self.x_seat += self.v_seat * dt
        
        return self.a_seat

class CushionSettlingMechanics:
    """Pre-Crash Dummy Gravity Settling & H-Point Initialization Engine.
    
    Models the static equilibrium settling of the occupant into the seat cushion
    prior to the dynamic crash pulse (t < 0).
    """
    @staticmethod
    def compute_initial_settling(occupant_mass_kg: float, cushion_stiffness_n_per_m: float) -> float:
        """Computes the static vertical cushion penetration (m) due to gravity."""
        g = 9.80665
        f_gravity = occupant_mass_kg * g
        # F = k * delta^1.5 (assuming Hunt-Crossley style or non-linear)
        # Using a simplified linearized approximation for initial static equilibrium
        settling_m = f_gravity / max(1.0, cushion_stiffness_n_per_m)
        return float(settling_m)
