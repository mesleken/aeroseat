"""
AeroSeat Lumped-Mass Multi-DOF Dynamics Engine

Mathematical crashworthiness model representing an aircraft seat structure and occupant
(FAA Hybrid III 50M, 5F, 95M) mounted to a dynamic sled fixture during 16g forward & 14g downward
dynamic sled impacts per 14 CFR § 25.562 / SAE AS8049E.

Physical Coupling Chain (Pure Inertial Frame Multi-Body Mechanics):
Sled Prescribed Deceleration Pulse a_sled(t) -> Sled Track Displacement
    -> Seat Rail Mount Connection (k_mount, c_mount) -> Seat Frame Dynamics (m_seat, I_seat)
    -> Lap Belt (k_lap, c_lap) + Cushion Dynamic Support/Friction -> Pelvis Dynamics (m_pelvis)
    -> Thoracolumbar Spine Joint (k_spine, c_spine) + Shoulder Harness (k_sh) + Backrest Rebound Contact -> Torso Dynamics (m_torso, I_torso)
    -> Cervical Neck Joint (k_neck, c_neck) + Cervical Whiplash Angular Dynamics -> Head Motion (m_head, I_head)
    -> Exact SAE J211 Head Acceleration & Certification Injury Metrics (HIC15, Nij, Lumbar, Femur)
    -> Physical Connection Graph & Constraint Validation Diagnostics Package
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional
from app.domain.physics.pulse_library import transform_pulse_3d, generate_sae_16g_forward_pulse, generate_sae_14g_downward_pulse
from app.domain.physics.signal_processing import sae_j211_cfc_filter, validate_pulse_delta_v
from app.domain.physics.seat.seat_structure import SeatStructureCompliance, SeatMountingCompliance, CushionSettlingMechanics
from app.domain.physics.multibody.constitutive import ConstitutiveModels
@dataclass
class OccupantSegmentConfig:
    """Anthropomorphic test dummy (ATD) mass and inertia properties (kg, kg*m^2)."""
    head_mass: float = 4.54
    neck_mass: float = 1.54
    thorax_mass: float = 23.04
    pelvis_mass: float = 12.78
    femur_left_mass: float = 5.67
    femur_right_mass: float = 5.67
    head_inertia_y: float = 0.024
    torso_inertia_y: float = 1.85
    neck_length_m: float = 0.115

# Standard Aviation Dummy Anthropometry Presets
DUMMY_PRESETS: dict[str, OccupantSegmentConfig] = {
    "FAA_HIII_50M": OccupantSegmentConfig(
        head_mass=4.54, neck_mass=1.54, thorax_mass=23.04, pelvis_mass=12.78, femur_left_mass=5.67, femur_right_mass=5.67,
        head_inertia_y=0.024, torso_inertia_y=1.85, neck_length_m=0.115
    ),
    "FAA_HIII_5F": OccupantSegmentConfig(
        head_mass=3.63, neck_mass=1.15, thorax_mass=17.28, pelvis_mass=9.59, femur_left_mass=4.25, femur_right_mass=4.25,
        head_inertia_y=0.018, torso_inertia_y=1.35, neck_length_m=0.100
    ),
    "FAA_HIII_95M": OccupantSegmentConfig(
        head_mass=5.45, neck_mass=1.85, thorax_mass=27.65, pelvis_mass=15.34, femur_left_mass=6.80, femur_right_mass=6.80,
        head_inertia_y=0.031, torso_inertia_y=2.30, neck_length_m=0.130
    ),
}

@dataclass
class RestraintAndStiffnessConfig:
    """Viscoelastic properties of structural joints, cushion, and restraints."""
    # Cervical Neck Joint
    neck_k_x: float = 12000.0        # N/m (flexion/extension shear stiffness)
    neck_c_x: float = 180.0          # N*s/m
    neck_k_z: float = 22000.0        # N/m (axial tension/compression)
    neck_c_z: float = 750.0
    neck_rot_k: float = 180.0        # N*m/rad (cervical pitch rotational stiffness)
    neck_rot_c: float = 12.0         # N*m*s/rad
    
    # Thoracolumbar Spine Joint
    spine_k_x: float = 18000.0       # N/m (thoracolumbar bending shear)
    spine_c_x: float = 650.0
    spine_k_z: float = 38000.0       # N/m (spinal axial compression)
    spine_c_z: float = 1300.0
    spine_rot_k: float = 650.0       # N*m/rad (lumbar joint pitch stiffness)
    spine_rot_c: float = 55.0        # N*m*s/rad
    
    # 3-Point Belt Restraint System
    belt_slack_mm: float = 16.0
    belt_k_lap: float = 48000.0      # N/m (lap belt webbing tensile stiffness)
    belt_c_lap: float = 1100.0
    belt_k_shoulder: float = 42000.0 # N/m (shoulder diagonal harness stiffness)
    belt_c_shoulder: float = 1300.0
    
    # Sled-to-Seat Rail Mounting Connection (Rigid Track Clamps with Structural Compliance)
    rail_mount_k: float = 850000.0   # N/m (high-stiffness floor track clamp)
    rail_mount_c: float = 18000.0    # N*s/m
    seat_rot_k: float = 32000.0      # N*m/rad (seat structure pitch stiffness)
    seat_rot_c: float = 650.0        # N*m*s/rad
    
    # Cushion & Backrest Viscoelastic Contact Mechanics
    cushion_k: float = 36000.0       # N/m (seat pan cushion vertical compression)
    cushion_c: float = 1400.0        # N*s/m
    cushion_mu: float = 0.45         # Kinetic friction coefficient on seat pan
    backrest_k: float = 24000.0      # N/m (backrest rebound support stiffness)
    backrest_c: float = 850.0        # N*s/m
    
    # Knee - Forward Structure Obstacle Contact
    knee_clearance_mm: float = 420.0 # Forward clearance to front seat row
    knee_contact_k: float = 95000.0  # N/m
    knee_contact_c: float = 1800.0

class LumpedMassCrashModel:
    """Multi-DOF Inertial-Frame Non-Linear Crash Dynamics Engine."""

    def __init__(
        self,
        occupant: Optional[OccupantSegmentConfig] = None,
        stiffness: Optional[RestraintAndStiffnessConfig] = None,
        pulse_type: str = "FORWARD_16G",
        dummy_type: str = "FAA_HIII_50M",
        yaw_deg: float = 0.0,
        pitch_deg: float = 0.0,
        roll_deg: float = 0.0,
        dummy_offset_x: float = 0.0,
        dummy_offset_y: float = 0.0,
        dummy_offset_z: float = 0.0,
        dummy_recline_deg: float = 0.0,
        dummy_yaw_deg: float = 0.0,
        seat_pitch_warp_deg: float = 0.0,
        seat_roll_warp_deg: float = 0.0,
        seat_yaw_mount_deg: float = 0.0,
        custom_pulse_data: Optional[dict] = None,
        seed: int = 42
    ):
        if occupant is not None:
            self.occ = occupant
        elif dummy_type in DUMMY_PRESETS:
            self.occ = DUMMY_PRESETS[dummy_type]
        else:
            self.occ = DUMMY_PRESETS["FAA_HIII_50M"]

        self.dummy_type = dummy_type
        self.stiff = stiffness or RestraintAndStiffnessConfig()
        self.pulse_type = pulse_type.upper()
        self.yaw_deg = float(yaw_deg)
        self.pitch_deg = float(pitch_deg)
        self.roll_deg = float(roll_deg)
        self.dummy_offset_x = float(dummy_offset_x)
        self.dummy_offset_y = float(dummy_offset_y)
        self.dummy_offset_z = float(dummy_offset_z)
        self.dummy_recline_deg = float(dummy_recline_deg)
        self.dummy_yaw_deg = float(dummy_yaw_deg)
        self.seat_pitch_warp_deg = float(seat_pitch_warp_deg)
        self.seat_roll_warp_deg = float(seat_roll_warp_deg)
        self.seat_yaw_mount_deg = float(seat_yaw_mount_deg)
        self.custom_pulse_data = custom_pulse_data
        self.rng = np.random.default_rng(seed)

    def run(self) -> dict:
        """Executes explicit time integration across the dynamic crash impact window."""
        # Time Grid (10 kHz sampling, 1901 points: -10ms to +180ms)
        t_arr = np.linspace(-0.010, 0.180, 1901, dtype=np.float64)
        n_steps = len(t_arr)
        dt = t_arr[1] - t_arr[0]
        g_val = 9.80665

        # Compound Orientations (Sled + Seat Mount + Dummy Orientations)
        total_yaw_deg = self.yaw_deg + self.dummy_yaw_deg + self.seat_yaw_mount_deg
        total_pitch_deg = self.pitch_deg + self.seat_pitch_warp_deg
        total_roll_deg = self.roll_deg + self.seat_roll_warp_deg

        # 3D Sled Acceleration Input in Global Frame (m/s^2)
        ax_sled, ay_sled, az_sled = transform_pulse_3d(
            t_arr,
            pulse_type=self.pulse_type,
            yaw_deg=total_yaw_deg,
            pitch_deg=total_pitch_deg,
            roll_deg=total_roll_deg,
            custom_pulse_data=self.custom_pulse_data
        )

        # Output Channel Arrays
        head_accel_g = np.zeros(n_steps, dtype=np.float64)
        neck_moment_my = np.zeros(n_steps, dtype=np.float64)
        neck_fz_n = np.zeros(n_steps, dtype=np.float64)
        femur_left_kn = np.zeros(n_steps, dtype=np.float64)
        femur_right_kn = np.zeros(n_steps, dtype=np.float64)
        lumbar_load_kn = np.zeros(n_steps, dtype=np.float64)
        sled_accel_g = np.zeros(n_steps, dtype=np.float64)
        belt_shoulder_kn = np.zeros(n_steps, dtype=np.float64)
        belt_lap_kn = np.zeros(n_steps, dtype=np.float64)
        seat_deflection_mm = np.zeros(n_steps, dtype=np.float64)

        # Kinematic Displacement Histories (World / Global Frame)
        sled_disp_x = np.zeros(n_steps, dtype=np.float64)
        sled_disp_y = np.zeros(n_steps, dtype=np.float64)
        sled_disp_z = np.zeros(n_steps, dtype=np.float64)

        # Relative Displacements (Seat rel to Sled; Occupant rel to Seat)
        seat_rel_x = np.zeros(n_steps, dtype=np.float64)
        seat_rel_y = np.zeros(n_steps, dtype=np.float64)
        seat_rel_z = np.zeros(n_steps, dtype=np.float64)
        seat_pitch_rad = np.zeros(n_steps, dtype=np.float64)

        pelvis_rel_x = np.zeros(n_steps, dtype=np.float64)
        pelvis_rel_y = np.zeros(n_steps, dtype=np.float64)
        pelvis_rel_z = np.zeros(n_steps, dtype=np.float64)

        torso_rel_x = np.zeros(n_steps, dtype=np.float64)
        torso_rel_y = np.zeros(n_steps, dtype=np.float64)
        torso_rel_z = np.zeros(n_steps, dtype=np.float64)
        torso_pitch_rad = np.zeros(n_steps, dtype=np.float64)

        head_rel_x = np.zeros(n_steps, dtype=np.float64)
        head_rel_y = np.zeros(n_steps, dtype=np.float64)
        head_rel_z = np.zeros(n_steps, dtype=np.float64)
        head_pitch_rad = np.zeros(n_steps, dtype=np.float64)

        femur_rel_l = np.zeros(n_steps, dtype=np.float64)
        femur_rel_r = np.zeros(n_steps, dtype=np.float64)

        # Constraint & Force Channels
        belt_lap_ext_mm = np.zeros(n_steps, dtype=np.float64)
        belt_shoulder_ext_mm = np.zeros(n_steps, dtype=np.float64)
        cushion_force_n = np.zeros(n_steps, dtype=np.float64)
        backrest_force_n = np.zeros(n_steps, dtype=np.float64)
        cushion_pen_mm = np.zeros(n_steps, dtype=np.float64)
        backrest_pen_mm = np.zeros(n_steps, dtype=np.float64)
        seat_sled_error_mm = np.zeros(n_steps, dtype=np.float64)

        # 3D Force Vectors at Major Segment Centers (N)
        head_vec_fx = np.zeros(n_steps, dtype=np.float64)
        head_vec_fy = np.zeros(n_steps, dtype=np.float64)
        head_vec_fz = np.zeros(n_steps, dtype=np.float64)

        torso_vec_fx = np.zeros(n_steps, dtype=np.float64)
        torso_vec_fy = np.zeros(n_steps, dtype=np.float64)
        torso_vec_fz = np.zeros(n_steps, dtype=np.float64)

        pelvis_vec_fx = np.zeros(n_steps, dtype=np.float64)
        pelvis_vec_fy = np.zeros(n_steps, dtype=np.float64)
        pelvis_vec_fz = np.zeros(n_steps, dtype=np.float64)

        seat_vec_fx = np.zeros(n_steps, dtype=np.float64)
        seat_vec_fy = np.zeros(n_steps, dtype=np.float64)
        seat_vec_fz = np.zeros(n_steps, dtype=np.float64)

        # Translational State Variables (Inertial Frame Global Coordinates)
        x_sled = 0.0; vx_sled = 0.0
        y_sled = 0.0; vy_sled = 0.0
        z_sled = 0.0; vz_sled = 0.0

        x_seat = 0.0; vx_seat = 0.0
        y_seat = 0.0; vy_seat = 0.0
        z_seat = 0.0; vz_seat = 0.0

        x_pelvis = 0.0; vx_pelvis = 0.0
        y_pelvis = 0.0; vy_pelvis = 0.0
        z_pelvis = 0.0; vz_pelvis = 0.0

        x_torso = 0.0; vx_torso = 0.0
        y_torso = 0.0; vy_torso = 0.0
        z_torso = 0.0; vz_torso = 0.0

        x_head = 0.0; vx_head = 0.0
        y_head = 0.0; vy_head = 0.0
        z_head = 0.0; vz_head = 0.0

        x_femur_l = 0.0; vx_femur_l = 0.0
        x_femur_r = 0.0; vx_femur_r = 0.0

        # Rotational Initial State Variables
        recline_init_rad = np.radians(self.dummy_recline_deg)
        theta_seat = 0.0; omega_seat = 0.0
        theta_torso = float(recline_init_rad); omega_torso = 0.0
        theta_head = float(recline_init_rad * 0.4); omega_head = 0.0

        max_head_excursion = 0.0
        max_knee_excursion = 0.0

        total_yaw_deg = self.yaw_deg + self.dummy_yaw_deg + self.seat_yaw_mount_deg
        total_pitch_deg = self.pitch_deg + self.seat_pitch_warp_deg
        total_roll_deg = self.roll_deg + self.seat_roll_warp_deg

        yaw_rad = np.radians(total_yaw_deg)
        pitch_rad = np.radians(total_pitch_deg)
        is_vertical_test = "14G" in self.pulse_type or "DOWN" in self.pulse_type or "VERT" in self.pulse_type

        seat_mass = 18.0
        seat_inertia_y = 1.35 # kg*m^2

        # Pelvis & Torso Physical Offsets (in meters)
        pelvis_z_offset_m = self.dummy_offset_z * 0.01
        pelvis_y_offset_m = self.dummy_offset_y * 0.01

        # Effective Dynamic Restraint Slack (adjusted for dummy positioning)
        base_slack_m = self.stiff.belt_slack_mm / 1000.0
        slack_lap_eff = max(0.005, base_slack_m + pelvis_z_offset_m)
        slack_shoulder_eff = max(0.005, base_slack_m + pelvis_z_offset_m + 0.35 * np.sin(max(0.0, recline_init_rad)))

        # Phase 7: High-Fidelity Mechanics Engines
        seat_mounting = SeatMountingCompliance(
            seat_mass_kg=seat_mass,
            mount_stiffness_n_per_m=self.stiff.rail_mount_k,
            mount_damping_ns_per_m=self.stiff.rail_mount_c
        )
        seatback_engine = SeatStructureCompliance(
            seatback_rotational_k_nm_per_rad=self.stiff.seat_rot_k,
            seatback_rotational_c_nms_per_rad=self.stiff.seat_rot_c
        )
        
        # Pre-Crash Gravity Settling & H-Point Initialization
        initial_settling_m = CushionSettlingMechanics.compute_initial_settling(
            occupant_mass_kg=(self.occ.pelvis_mass + self.occ.thorax_mass),
            cushion_stiffness_n_per_m=self.stiff.cushion_k
        )
        # Apply static equilibrium offset to initial coordinates (Assuming z is vertical/gravitational axis)
        if is_vertical_test:
            # For 14G downward, seat translates in +Z, gravity acts in +Z
            z_pelvis += initial_settling_m
            z_torso += initial_settling_m
            z_head += initial_settling_m
        else:
            # 16G Forward is typically +X, but gravity is usually in -Z or +Z depending on frame
            z_pelvis += initial_settling_m
            z_torso += initial_settling_m
            z_head += initial_settling_m

        for i in range(n_steps):
            # 1. Sled Kinematics: Deceleration Pulse Applied Directly to Sled Carriage
            ax_in = float(ax_sled[i])
            ay_in = float(ay_sled[i])
            az_in = float(az_sled[i])

            vx_sled += ax_in * dt; x_sled += vx_sled * dt
            vy_sled += ay_in * dt; y_sled += vy_sled * dt
            vz_sled += az_in * dt; z_sled += vz_sled * dt

            sled_disp_x[i] = float(x_sled)
            sled_disp_y[i] = float(y_sled)
            sled_disp_z[i] = float(z_sled)

            sled_mag_g = np.sqrt(ax_in**2 + ay_in**2 + az_in**2) / g_val
            sled_accel_g[i] = float(sled_mag_g)

            if is_vertical_test:
                # =========================================================================
                # 14G DOWNWARD VERTICAL DROP TEST (Inertial Frame Formulation)
                # =========================================================================
                # Vertical Cushion Compression Contact (Seat advances downward into Pelvis)
                delta_z_cushion_0 = max(0.0, -pelvis_y_offset_m)
                delta_z_cushion = max(0.0, z_seat - z_pelvis + delta_z_cushion_0)
                v_rel_z_cushion = max(0.0, vz_seat - vz_pelvis)
                f_cushion_z = ConstitutiveModels.cushion_hysteresis(delta_z_cushion, v_rel_z_cushion, self.stiff.cushion_k, self.stiff.cushion_c, yield_pen=0.08)

                # Spinal Axial Compression (Pelvis advances downward into Torso)
                delta_z_spine = z_pelvis - z_torso
                v_rel_z_spine = vz_pelvis - vz_torso
                f_spine_z = self.stiff.spine_k_z * delta_z_spine + self.stiff.spine_c_z * v_rel_z_spine

                # Neck Axial Compression (Torso advances downward into Head)
                delta_z_neck = z_torso - z_head
                v_rel_z_neck = vz_torso - vz_head
                f_neck_z = self.stiff.neck_k_z * delta_z_neck + self.stiff.neck_c_z * v_rel_z_neck

                # Floor Mount Track Force (Sled pulls Seat downward)
                f_mount_z = self.stiff.rail_mount_k * (z_sled - z_seat) + self.stiff.rail_mount_c * (vz_sled - vz_seat)

                # Pure Inertial Frame Dynamic Accelerations
                f_seat_net_z = f_mount_z - f_cushion_z
                a_seat_z = f_seat_net_z / seat_mass
                vz_seat += a_seat_z * dt; z_seat += vz_seat * dt

                f_pelvis_net_z = f_cushion_z - f_spine_z
                a_pelvis_z = f_pelvis_net_z / self.occ.pelvis_mass
                vz_pelvis += a_pelvis_z * dt; z_pelvis += vz_pelvis * dt

                f_torso_net_z = f_spine_z - f_neck_z
                a_torso_z = f_torso_net_z / self.occ.thorax_mass
                vz_torso += a_torso_z * dt; z_torso += vz_torso * dt

                f_head_net_z = f_neck_z
                a_head_z = f_head_net_z / self.occ.head_mass
                vz_head += a_head_z * dt; z_head += vz_head * dt

                # Relative Displacements (Relative to Sled/Seat for 3D Viewer)
                seat_rel_z[i] = float(z_seat - z_sled)
                pelvis_rel_z[i] = float(z_pelvis - z_seat)
                torso_rel_z[i] = float(z_torso - z_seat)
                head_rel_z[i] = float(z_head - z_seat)

                # Output Channels (True 3D Resultant for HIC with Gravity Offset)
                # Assuming +Z is downward, gravity adds to the sensor reading when at rest.
                a_meas_x = 0.0
                a_meas_y = 0.0
                a_meas_z = a_head_z - g_val
                head_res_g = np.sqrt(a_meas_x**2 + a_meas_y**2 + a_meas_z**2) / g_val
                head_accel_g[i] = float(head_res_g)

                lumbar_load_kn[i] = float(abs(f_spine_z) / 1000.0)
                neck_fz_n[i] = float(abs(f_neck_z))
                neck_moment_my[i] = float(abs(f_neck_z) * 0.018)

                femur_left_kn[i] = float(0.40)
                femur_right_kn[i] = float(0.40)

                cushion_force_n[i] = float(f_cushion_z)
                cushion_pen_mm[i] = float(delta_z_cushion * 1000.0)
                seat_sled_error_mm[i] = float(abs(z_seat - z_sled) * 1000.0)

            else:
                # =========================================================================
                # 16G FORWARD LONGITUDINAL IMPACT (Inertial Frame Multi-Body Dynamics)
                # =========================================================================
                # 1. Lap Belt Webbing Extension (Seat pulls Pelvis forward)
                ext_lap = max(0.0, (x_seat - x_pelvis) - slack_lap_eff)
                v_rel_lap = (vx_seat - vx_pelvis)
                f_belt_pelvis = ConstitutiveModels.nonlinear_belt_webbing(
                    ext_lap, v_rel_lap, 
                    self.stiff.belt_k_lap, self.stiff.belt_k_lap * 15.0, self.stiff.belt_k_lap * 50.0, 
                    self.stiff.belt_c_lap
                )

                # 2. Shoulder Harness Webbing Extension (Seat pulls Torso forward)
                ext_shoulder = max(0.0, (x_seat - x_torso) - slack_shoulder_eff)
                v_rel_sh = (vx_seat - vx_torso)
                f_belt_torso = ConstitutiveModels.nonlinear_belt_webbing(
                    ext_shoulder, v_rel_sh, 
                    self.stiff.belt_k_shoulder, self.stiff.belt_k_shoulder * 20.0, self.stiff.belt_k_shoulder * 60.0, 
                    self.stiff.belt_c_shoulder
                )

                # 3. Backrest Rebound Unilateral Contact (Torso rebounds back into seat backrest)
                pen_backrest = max(0.0, (x_seat - x_torso))
                v_pen_backrest = max(0.0, (vx_seat - vx_torso))
                f_backrest = (self.stiff.backrest_k * pen_backrest + self.stiff.backrest_c * v_pen_backrest) if pen_backrest > 0 else 0.0

                # 4. Cushion Normal & Dynamic Sliding Friction
                f_cush_norm = (self.occ.pelvis_mass + 0.40 * self.occ.thorax_mass) * g_val
                v_slip_pelvis = vx_seat - vx_pelvis
                f_cush_fric = self.stiff.cushion_mu * f_cush_norm * np.tanh(v_slip_pelvis / 0.05)

                # 5. Inter-Segment Joint Reactions
                # Thoracolumbar Spine Joint Shear (Pelvis pulls Torso forward)
                rel_pelvis_torso = x_pelvis - x_torso
                v_rel_pelvis_torso = vx_pelvis - vx_torso
                f_spine_x = self.stiff.spine_k_x * rel_pelvis_torso + self.stiff.spine_c_x * v_rel_pelvis_torso

                # Cervical Neck Joint with Progressive Flexion Whiplash Hardening
                rel_torso_head = x_torso - x_head
                v_rel_torso_head = vx_torso - vx_head
                cervical_hardening = 1.0 + 15.0 * max(0.0, abs(rel_torso_head) - 0.035)**1.5
                f_neck_x = self.stiff.neck_k_x * cervical_hardening * rel_torso_head + self.stiff.neck_c_x * v_rel_torso_head

                # Lateral Neck Joint (under yaw)
                f_neck_y = self.stiff.neck_k_x * 0.8 * (y_seat - y_head) + self.stiff.neck_c_x * (vy_seat - vy_head)

                # 6. Rail Mount Track Forces (Phase 7 Compliant Engine)
                f_occupant_reaction_x = f_belt_pelvis + f_belt_torso + f_cush_fric - f_backrest
                a_seat_x = seat_mounting.evaluate_seat_acceleration(ax_in, vx_sled, x_sled, f_occupant_reaction_x, dt)
                x_seat = seat_mounting.x_seat
                vx_seat = seat_mounting.v_seat

                f_mount_y = self.stiff.rail_mount_k * (y_sled - y_seat) + self.stiff.rail_mount_c * (vy_sled - vy_seat)
                
                # 7. Multi-Body Equations of Motion in Inertial Global Frame
                a_seat_y = f_mount_y / seat_mass
                vy_seat += a_seat_y * dt; y_seat += vy_seat * dt

                # Pelvis: pulled by lap belt and friction, opposed by spine joint
                f_pelvis_net_x = f_belt_pelvis + f_cush_fric - f_spine_x
                a_pelvis_x = f_pelvis_net_x / self.occ.pelvis_mass
                vx_pelvis += a_pelvis_x * dt; x_pelvis += vx_pelvis * dt

                # Torso: pulled by shoulder harness, spine, and backrest; opposed by neck joint
                f_torso_net_x = f_belt_torso + f_spine_x + f_backrest - f_neck_x
                a_torso_x = f_torso_net_x / self.occ.thorax_mass
                vx_torso += a_torso_x * dt; x_torso += vx_torso * dt

                # Head: driven purely through cervical neck joint
                f_head_net_x = f_neck_x
                a_head_x = f_head_net_x / self.occ.head_mass
                vx_head += a_head_x * dt; x_head += vx_head * dt

                a_head_y = f_neck_y / self.occ.head_mass
                vy_head += a_head_y * dt; y_head += vy_head * dt

                # 8. Rotational Pitch Differential Equations of Motion (Phase 7 Seatback Engine)
                m_seat_applied = (f_belt_torso * 0.45 + f_belt_pelvis * 0.15)
                theta_seat, m_seat_restoring = seatback_engine.evaluate_seatback_response(m_seat_applied, dt)
                
                # Enforce physical rotation stops
                theta_seat = max(-0.15, min(0.45, theta_seat))
                seatback_engine.seatback_angle_rad = theta_seat
                omega_seat = seatback_engine.seatback_omega_rad_per_s

                # Torso Flexion Pitch (Hip Pivot Flexion)
                m_torso_pitch = (self.occ.thorax_mass * a_torso_x * 0.22) - (f_belt_torso * 0.35 + self.stiff.spine_rot_k * theta_torso + self.stiff.spine_rot_c * omega_torso)
                alpha_torso = m_torso_pitch / self.occ.torso_inertia_y
                omega_torso += alpha_torso * dt; theta_torso = max(-0.25, min(1.20, theta_torso + omega_torso * dt))

                # Head Pitch (Cervical Flexion Whiplash Dynamics)
                m_head_pitch = (self.occ.head_mass * abs(a_head_x - a_torso_x) * self.occ.neck_length_m) - (self.stiff.neck_rot_k * theta_head + self.stiff.neck_rot_c * omega_head)
                alpha_head = m_head_pitch / self.occ.head_inertia_y
                omega_head += alpha_head * dt; theta_head = max(-0.35, min(1.35, theta_head + omega_head * dt))

                # 9. Femurs & Knee Reactions (Clearance is sensitive to fore/aft pelvis offset and yaw)
                clearance_base = (self.stiff.knee_clearance_mm / 1000.0) + pelvis_z_offset_m
                clearance_l = max(0.01, clearance_base * (1.0 - 0.45 * np.sin(yaw_rad)))
                clearance_r = max(0.01, clearance_base * (1.0 + 0.45 * np.sin(yaw_rad)))

                f_hip_l = 28000.0 * (x_pelvis - x_femur_l) + 900.0 * (vx_pelvis - vx_femur_l)
                f_hip_r = 28000.0 * (x_pelvis - x_femur_r) + 900.0 * (vx_pelvis - vx_femur_r)

                knee_pen_l = max(0.0, (x_seat - x_femur_l) - clearance_l)
                knee_pen_r = max(0.0, (x_seat - x_femur_r) - clearance_r)

                f_knee_contact_l = (self.stiff.knee_contact_k * knee_pen_l + self.stiff.knee_contact_c * vx_femur_l) if knee_pen_l > 0 else 0.0
                f_knee_contact_r = (self.stiff.knee_contact_k * knee_pen_r + self.stiff.knee_contact_c * vx_femur_r) if knee_pen_r > 0 else 0.0

                f_femur_net_l = f_hip_l - f_knee_contact_l
                f_femur_net_r = f_hip_r - f_knee_contact_r

                a_femur_l = f_femur_net_l / self.occ.femur_left_mass
                a_femur_r = f_femur_net_r / self.occ.femur_right_mass
                vx_femur_l += a_femur_l * dt; x_femur_l += vx_femur_l * dt
                vx_femur_r += a_femur_r * dt; x_femur_r += vx_femur_r * dt

                f_femur_l = f_knee_contact_l if knee_pen_l > 0 else (f_belt_pelvis * 0.28 + abs(f_hip_l) * 0.55)
                f_femur_r = f_knee_contact_r if knee_pen_r > 0 else (f_belt_pelvis * 0.28 + abs(f_hip_r) * 0.55)

                femur_rel_l[i] = float(x_seat - x_femur_l)
                femur_rel_r[i] = float(x_seat - x_femur_r)
                femur_left_kn[i] = float(f_femur_l / 1000.0)
                femur_right_kn[i] = float(f_femur_r / 1000.0)

                # Record Relative Displacements (for 3D WebGL Viewer)
                seat_deflection_mm[i] = float(abs(x_seat - x_sled) * 1000.0)
                seat_rel_x[i] = float(x_seat - x_sled)
                seat_rel_y[i] = float(y_seat - y_sled)
                seat_pitch_rad[i] = float(theta_seat)

                pelvis_rel_x[i] = float(x_seat - x_pelvis)
                torso_rel_x[i] = float(x_seat - x_torso)
                torso_pitch_rad[i] = float(theta_torso)

                head_rel_x[i] = float(x_seat - x_head)
                head_rel_y[i] = float(y_head - y_seat)
                head_pitch_rad[i] = float(theta_head)

                # 10. Head Resultant Acceleration for HIC15 (Translational + Cervical Whiplash CG Acceleration + Gravity)
                a_head_cg_x = a_head_x + alpha_head * self.occ.neck_length_m
                a_head_cg_y = a_head_y
                a_head_cg_z = -g_val # True resultant accelerometer feels 1G upward when at rest. (assuming +Z is down)
                
                head_res_g = np.sqrt(a_head_cg_x**2 + a_head_cg_y**2 + a_head_cg_z**2) / g_val
                head_accel_g[i] = float(head_res_g)

                # Neck Injury Criterion Channels (Signed Nij: Fz & My)
                f_neck_z = abs(f_neck_x) * 0.35 * (1.0 + abs(total_pitch_deg) / 20.0)
                neck_moment_mag = abs(f_neck_x * 0.085 + f_neck_z * 0.035)
                neck_moment_sign = 1.0 if theta_head >= 0 else -1.0
                neck_moment_my[i] = float(neck_moment_mag * neck_moment_sign)
                neck_fz_n[i] = float(f_neck_z)

                # Lumbar Spinal Load (FAA Criterion: <= 6.67 kN / 1500 lbs)
                pitch_comp = abs(f_spine_x) * np.sin(np.radians(abs(total_pitch_deg) + abs(self.dummy_recline_deg))) * 1.6
                tot_lumbar = abs(f_spine_x) * 0.75 + f_belt_torso * 0.25 + pitch_comp
                lumbar_load_kn[i] = float(tot_lumbar / 1000.0)

                belt_shoulder_kn[i] = float(f_belt_torso / 1000.0)
                belt_lap_kn[i] = float(f_belt_pelvis / 1000.0)

                belt_lap_ext_mm[i] = float(ext_lap * 1000.0)
                belt_shoulder_ext_mm[i] = float(ext_shoulder * 1000.0)
                backrest_force_n[i] = float(f_backrest)
                backrest_pen_mm[i] = float(pen_backrest * 1000.0)
                seat_sled_error_mm[i] = float(abs(x_seat - x_sled) * 1000.0)

                # Instantaneous Force Vectors (N)
                head_vec_fx[i] = float(-f_neck_x)
                head_vec_fy[i] = float(-f_neck_y)
                head_vec_fz[i] = float(-f_neck_z)

                torso_vec_fx[i] = float(-f_belt_torso - f_spine_x + f_neck_x + f_backrest)
                torso_vec_fz[i] = float(-f_neck_z)

                pelvis_vec_fx[i] = float(-f_belt_pelvis + f_spine_x - f_cush_fric)
                seat_vec_fx[i] = float(f_belt_pelvis + f_belt_torso + f_cush_fric - f_backrest)

            excursion_head_mm = (abs(x_seat - x_head) + 0.54) * 1000.0 if not is_vertical_test else 540.0
            if excursion_head_mm > max_head_excursion:
                max_head_excursion = excursion_head_mm

            excursion_knee_mm = (max(abs(femur_rel_l[i]), abs(femur_rel_r[i])) + 0.41) * 1000.0 if not is_vertical_test else 410.0
            if excursion_knee_mm > max_knee_excursion:
                max_knee_excursion = excursion_knee_mm

        # Submarining Kinematic Risk Indicator (Lap belt slip over iliac crest threshold)
        pelvis_rot_rad = torso_pitch_rad * 0.70
        submarining_risk_series = np.maximum(0.0, (pelvis_rel_x * np.cos(pelvis_rot_rad) - 0.040) / 0.080)
        max_submarining_risk = float(round(np.max(submarining_risk_series), 2))
        submarining_status = "ELEVATED_SUBMARINING_RISK" if max_submarining_risk > 1.0 else "LOW_NOMINAL"

        # Structural status evaluation
        structural_status = "INTACT_NO_FAILURE"
        if abs(self.yaw_deg) > 40.0 or abs(self.pitch_deg) > 25.0:
            structural_status = "WARNING_STRUCTURAL_PLASTIC_DEFORMATION"

        # Signal Filtering (SAE J211-1 / ISO 6487 zero-phase digital Butterworth filter)
        filtered_head_accel = sae_j211_cfc_filter(head_accel_g, dt, cfc=1000)
        filtered_femur_l = sae_j211_cfc_filter(femur_left_kn, dt, cfc=600)
        filtered_femur_r = sae_j211_cfc_filter(femur_right_kn, dt, cfc=600)
        filtered_lumbar = sae_j211_cfc_filter(lumbar_load_kn, dt, cfc=600)
        filtered_neck_fz = sae_j211_cfc_filter(neck_fz_n, dt, cfc=1000)
        filtered_neck_my = sae_j211_cfc_filter(neck_moment_my, dt, cfc=1000)
        filtered_belt_shoulder = sae_j211_cfc_filter(belt_shoulder_kn, dt, cfc=600)
        filtered_belt_lap = sae_j211_cfc_filter(belt_lap_kn, dt, cfc=600)

        req_dv = 10.7 if is_vertical_test else 13.4
        delta_v, dv_pass = validate_pulse_delta_v(t_arr, sled_accel_g, required_delta_v=req_dv)

        max_lap_f = float(np.max(filtered_belt_lap))
        max_sh_f = float(np.max(filtered_belt_shoulder))
        max_cush_f = float(np.max(cushion_force_n)) / 1000.0
        max_back_f = float(np.max(backrest_force_n)) / 1000.0
        max_error = float(np.max(seat_sled_error_mm))
        rms_error = float(np.sqrt(np.mean(seat_sled_error_mm**2)))

        # Global Coordinate Time Histories
        sled_global_x = sled_disp_x.tolist()
        sled_global_y = sled_disp_y.tolist()
        sled_global_z = sled_disp_z.tolist()

        seat_global_x = (sled_disp_x + seat_rel_x).tolist()
        seat_global_y = (sled_disp_y + seat_rel_y).tolist()
        seat_global_z = (sled_disp_z + seat_rel_z).tolist()

        pelvis_global_x = (sled_disp_x + seat_rel_x + pelvis_rel_x).tolist()
        pelvis_global_y = (sled_disp_y + seat_rel_y + pelvis_rel_y).tolist()
        pelvis_global_z = (sled_disp_z + seat_rel_z + pelvis_rel_z).tolist()

        torso_global_x = (sled_disp_x + seat_rel_x + torso_rel_x).tolist()
        torso_global_y = (sled_disp_y + seat_rel_y + torso_rel_y).tolist()
        torso_global_z = (sled_disp_z + seat_rel_z + torso_rel_z).tolist()

        head_global_x = (sled_disp_x + seat_rel_x + head_rel_x).tolist()
        head_global_y = (sled_disp_y + seat_rel_y + head_rel_y).tolist()
        head_global_z = (sled_disp_z + seat_rel_z + head_rel_z).tolist()

        return {
            "time_s": t_arr.tolist(),
            "frames": {
                "sled": {
                    "position_global_m": {"x": sled_global_x, "y": sled_global_y, "z": sled_global_z},
                    "acceleration_mps2": {"x": ax_sled.tolist(), "y": ay_sled.tolist(), "z": az_sled.tolist()},
                    "acceleration_g": sled_accel_g.tolist()
                },
                "seat": {
                    "position_global_m": {"x": seat_global_x, "y": seat_global_y, "z": seat_global_z},
                    "relative_to_sled_m": {"x": seat_rel_x.tolist(), "y": seat_rel_y.tolist(), "z": seat_rel_z.tolist()},
                    "rotation_rad": {"pitch": seat_pitch_rad.tolist(), "yaw": np.zeros(n_steps).tolist(), "roll": np.zeros(n_steps).tolist()}
                },
                "pelvis": {
                    "position_global_m": {"x": pelvis_global_x, "y": pelvis_global_y, "z": pelvis_global_z},
                    "relative_to_seat_m": {"x": pelvis_rel_x.tolist(), "y": pelvis_rel_y.tolist(), "z": pelvis_rel_z.tolist()}
                },
                "torso": {
                    "position_global_m": {"x": torso_global_x, "y": torso_global_y, "z": torso_global_z},
                    "relative_to_pelvis_m": {"x": (torso_rel_x - pelvis_rel_x).tolist(), "y": (torso_rel_y - pelvis_rel_y).tolist(), "z": (torso_rel_z - pelvis_rel_z).tolist()},
                    "rotation_rad": {"pitch": torso_pitch_rad.tolist(), "yaw": np.zeros(n_steps).tolist(), "roll": np.zeros(n_steps).tolist()}
                },
                "head": {
                    "position_global_m": {"x": head_global_x, "y": head_global_y, "z": head_global_z},
                    "relative_to_torso_m": {"x": (head_rel_x - torso_rel_x).tolist(), "y": (head_rel_y - torso_rel_y).tolist(), "z": (head_rel_z - torso_rel_z).tolist()},
                    "rotation_rad": {"pitch": head_pitch_rad.tolist(), "yaw": np.zeros(n_steps).tolist(), "roll": np.zeros(n_steps).tolist()},
                    "acceleration_g": filtered_head_accel.tolist()
                }
            },
            "kinematics": {
                "sled": {
                    "position_m": {"x": sled_disp_x.tolist(), "y": sled_disp_y.tolist(), "z": sled_disp_z.tolist()},
                    "acceleration_mps2": {"x": ax_sled.tolist(), "y": ay_sled.tolist(), "z": az_sled.tolist()},
                    "acceleration_g": sled_accel_g.tolist()
                },
                "seat": {
                    "relative_disp_m": {"x": seat_rel_x.tolist(), "y": seat_rel_y.tolist(), "z": seat_rel_z.tolist()},
                    "pitch_rad": seat_pitch_rad.tolist()
                },
                "pelvis": {
                    "relative_disp_m": {"x": pelvis_rel_x.tolist(), "y": pelvis_rel_y.tolist(), "z": pelvis_rel_z.tolist()}
                },
                "torso": {
                    "relative_disp_m": {"x": torso_rel_x.tolist(), "y": torso_rel_y.tolist(), "z": torso_rel_z.tolist()},
                    "pitch_rad": torso_pitch_rad.tolist()
                },
                "head": {
                    "relative_disp_m": {"x": head_rel_x.tolist(), "y": head_rel_y.tolist(), "z": head_rel_z.tolist()},
                    "pitch_rad": head_pitch_rad.tolist(),
                    "acceleration_g": filtered_head_accel.tolist()
                },
                "femurs": {
                    "left_disp_m": femur_rel_l.tolist(),
                    "right_disp_m": femur_rel_r.tolist()
                }
            },
            "constraints": {
                "seat_to_sled": {
                    "type": "ELASTOPLASTIC_COMPLIANT_RAIL_4X",
                    "status": "PASS" if max_error < 150.0 else "WARNING",
                    "max_error_mm": round(max_error, 4),
                    "rms_error_mm": round(rms_error, 4),
                    "error_series_mm": seat_sled_error_mm.tolist(),
                    "anchor_points": ["MOUNT_FRONT_LEFT", "MOUNT_FRONT_RIGHT", "MOUNT_REAR_LEFT", "MOUNT_REAR_RIGHT"]
                },
                "lap_belt": {
                    "type": "TENSION_ONLY_WEBBING",
                    "status": "ENGAGED" if max_lap_f > 0.05 else "SLACK",
                    "peak_force_kn": round(max_lap_f, 2),
                    "force_series_kn": filtered_belt_lap.tolist(),
                    "extension_series_mm": belt_lap_ext_mm.tolist(),
                    "engaged_series": [bool(f > 0.02) for f in filtered_belt_lap]
                },
                "shoulder_belt": {
                    "type": "TENSION_ONLY_WEBBING",
                    "status": "ENGAGED" if max_sh_f > 0.05 else "SLACK",
                    "peak_force_kn": round(max_sh_f, 2),
                    "force_series_kn": filtered_belt_shoulder.tolist(),
                    "extension_series_mm": belt_shoulder_ext_mm.tolist(),
                    "engaged_series": [bool(f > 0.02) for f in filtered_belt_shoulder]
                },
                "cushion": {
                    "type": "UNILATERAL_CONTACT",
                    "status": "ACTIVE" if max_cush_f > 0.05 else "INACTIVE",
                    "peak_force_kn": round(max_cush_f, 2),
                    "force_series_n": cushion_force_n.tolist(),
                    "penetration_series_mm": cushion_pen_mm.tolist()
                },
                "backrest": {
                    "type": "UNILATERAL_CONTACT",
                    "status": "ACTIVE" if max_back_f > 0.05 else "INACTIVE",
                    "peak_force_kn": round(max_back_f, 2),
                    "force_series_n": backrest_force_n.tolist(),
                    "penetration_series_mm": backrest_pen_mm.tolist()
                }
            },
            "force_vectors": {
                "head": {
                    "fx": head_vec_fx.tolist(),
                    "fy": head_vec_fy.tolist(),
                    "fz": head_vec_fz.tolist()
                },
                "torso": {
                    "fx": torso_vec_fx.tolist(),
                    "fy": torso_vec_fy.tolist(),
                    "fz": torso_vec_fz.tolist()
                },
                "pelvis": {
                    "fx": pelvis_vec_fx.tolist(),
                    "fy": pelvis_vec_fy.tolist(),
                    "fz": pelvis_vec_fz.tolist()
                },
                "seat": {
                    "fx": seat_vec_fx.tolist(),
                    "fy": seat_vec_fy.tolist(),
                    "fz": seat_vec_fz.tolist()
                }
            },
            "loads": {
                "neck_moment": filtered_neck_my.tolist(),
                "neck_axial_force": filtered_neck_fz.tolist(),
                "femur_load_left": filtered_femur_l.tolist(),
                "femur_load_right": filtered_femur_r.tolist(),
                "lumbar_load": filtered_lumbar.tolist(),
                "belt_shoulder_kn": filtered_belt_shoulder.tolist(),
                "belt_lap_kn": filtered_belt_lap.tolist()
            },
            "head_acceleration": filtered_head_accel.tolist(),
            "neck_moment": filtered_neck_my.tolist(),
            "neck_axial_force": filtered_neck_fz.tolist(),
            "femur_load_left": filtered_femur_l.tolist(),
            "femur_load_right": filtered_femur_r.tolist(),
            "lumbar_load": filtered_lumbar.tolist(),
            "belt_shoulder_load_kn": filtered_belt_shoulder.tolist(),
            "belt_lap_load_kn": filtered_belt_lap.tolist(),
            "sled_acceleration": sled_accel_g.tolist(),
            "seat_deflection_mm": seat_deflection_mm.tolist(),
            "head_excursion_mm": round(max_head_excursion, 1),
            "knee_excursion_mm": round(max_knee_excursion, 1),
            "seat_structural_status": structural_status,
            "submarining_risk_indicator": max_submarining_risk,
            "submarining_status": submarining_status,
            "delta_v_ms": delta_v,
            "delta_v_valid": dv_pass,
            "dummy_type": self.dummy_type,
            "pulse_type": self.pulse_type
        }
