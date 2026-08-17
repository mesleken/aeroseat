import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List

from app.domain.physics.pulse_library import transform_pulse_3d, compute_euler_rotation_matrix
from app.domain.physics.signal_processing import sae_j211_cfc_filter, validate_pulse_delta_v
from app.domain.physics.seat.seat_structure import (
    SeatMountingCompliance,
    SeatStructureCompliance,
    CushionSettlingMechanics
)
from app.domain.physics.multibody.constitutive import ConstitutiveModels
from app.domain.physics.multibody.contact_geometry import ObstacleContactEngine, FlailEnvelopeContactConfig, ObstacleSurface
from app.domain.physics.multibody.articulated_joint import ArticulatedJoint, ArticulatedJointConfig

@dataclass
class OccupantSegmentConfig:
    """Anthropometric segment definitions for FAA Hybrid III Test Dummies (Full 77.7 kg Hybrid III 50M)."""
    head_mass: float = 4.54          # kg
    neck_mass: float = 1.54          # kg
    thorax_mass: float = 23.04       # kg
    pelvis_mass: float = 14.80       # kg
    femur_left_mass: float = 5.90    # kg
    femur_right_mass: float = 5.90   # kg
    tibia_left_mass: float = 4.65    # kg (lower leg)
    tibia_right_mass: float = 4.65   # kg (lower leg)
    foot_left_mass: float = 1.25     # kg
    foot_right_mass: float = 1.25    # kg
    arms_mass: float = 10.10         # kg (coupled to torso)
    head_inertia_y: float = 0.024    # kg*m^2 (Pitch axis)
    torso_inertia_y: float = 1.85    # kg*m^2 (Pitch axis)
    neck_length_m: float = 0.115     # m (115 mm OC-to-T1 lever arm)

    @property
    def total_dummy_mass_kg(self) -> float:
        """Returns total anthropometric dummy mass in kg (~77.7 kg for 50M)."""
        return (
            self.head_mass + self.neck_mass + self.thorax_mass + self.pelvis_mass +
            self.femur_left_mass + self.femur_right_mass + self.tibia_left_mass +
            self.tibia_right_mass + self.foot_left_mass + self.foot_right_mass + self.arms_mass
        )

DUMMY_PRESETS = {
    "FAA_HIII_50M": OccupantSegmentConfig(
        head_mass=4.54, neck_mass=1.54, thorax_mass=23.04, pelvis_mass=14.80,
        femur_left_mass=5.90, femur_right_mass=5.90,
        tibia_left_mass=4.65, tibia_right_mass=4.65,
        foot_left_mass=1.25, foot_right_mass=1.25, arms_mass=10.10,
        head_inertia_y=0.024, torso_inertia_y=1.85, neck_length_m=0.115
    ),
    "FAA_HIII_5F": OccupantSegmentConfig(
        head_mass=3.63, neck_mass=1.15, thorax_mass=17.28, pelvis_mass=11.10,
        femur_left_mass=4.42, femur_right_mass=4.42,
        tibia_left_mass=3.48, tibia_right_mass=3.48,
        foot_left_mass=0.94, foot_right_mass=0.94, arms_mass=7.58,
        head_inertia_y=0.018, torso_inertia_y=1.35, neck_length_m=0.100
    ),
    "FAA_HIII_95M": OccupantSegmentConfig(
        head_mass=5.45, neck_mass=1.85, thorax_mass=27.65, pelvis_mass=17.76,
        femur_left_mass=7.08, femur_right_mass=7.08,
        tibia_left_mass=5.58, tibia_right_mass=5.58,
        foot_left_mass=1.50, foot_right_mass=1.50, arms_mass=12.12,
        head_inertia_y=0.031, torso_inertia_y=2.30, neck_length_m=0.130
    ),
}

@dataclass
class BeltAnchorGeometry:
    """3D Spatial Anchor Locations for 3-Point Aviation Restraint Routing."""
    d_ring_xyz: tuple[float, float, float] = (0.28, 0.22, -0.42)   # Upper shoulder harness guide (m)
    buckle_xyz: tuple[float, float, float] = (0.02, 0.18, 0.06)     # Central stalk buckle latch (m)
    lap_anchor_l: tuple[float, float, float] = (-0.05, -0.22, 0.08) # Outboard pelvic attachment (m)
    lap_anchor_r: tuple[float, float, float] = (-0.05, 0.22, 0.08)  # Inboard pelvic attachment (m)

@dataclass
class RestraintAndStiffnessConfig:
    """Viscoelastic properties of structural joints, cushion, and restraints (Phase 12 Industrial MBD Defaults)."""
    # Cervical Neck Joint (Hunt-Crossley Non-Linear Joint)
    neck_k_x: float = 14000.0        # N/m (flexion/extension shear stiffness)
    neck_c_x: float = 240.0          # N*s/m
    neck_k_z: float = 28000.0        # N/m (axial tension/compression)
    neck_c_z: float = 850.0          # N*s/m
    neck_rot_k: float = 220.0        # N*m/rad (cervical pitch rotational stiffness)
    neck_rot_c: float = 16.0         # N*m*s/rad
    
    # Thoracolumbar Spine Joint
    spine_k_x: float = 22000.0       # N/m (thoracolumbar bending shear)
    spine_c_x: float = 800.0         # N*s/m
    spine_k_z: float = 48000.0       # N/m (spinal axial compression)
    spine_c_z: float = 1600.0        # N*s/m
    spine_rot_k: float = 750.0       # N*m/rad (lumbar joint pitch stiffness)
    spine_rot_c: float = 65.0        # N*m*s/rad
    
    # 3-Point Belt Restraint System (Aviation High-Tenacity Polyester Webbing)
    belt_slack_mm: float = 16.0      # mm (geometric slack)
    belt_film_spool_mm: float = 30.0 # mm (retractor spool-out effect)
    belt_k_lap: float = 120000.0     # N/m (lap belt webbing tensile stiffness)
    belt_c_lap: float = 2200.0       # N*s/m
    belt_k_shoulder: float = 95000.0 # N/m (shoulder diagonal harness stiffness)
    belt_c_shoulder: float = 2800.0  # N*s/m
    belt_anchors: BeltAnchorGeometry = field(default_factory=BeltAnchorGeometry)
    
    # Sled-to-Seat Rail Mounting Connection (Elastoplastic Floor Track Clamps)
    rail_mount_k: float = 850000.0   # N/m (high-stiffness floor track clamp)
    rail_mount_c: float = 18000.0    # N*s/m
    floor_elastic_k: float = 8500000.0 # N/m (aircraft fuselage floor compliance)
    floor_elastic_c: float = 45000.0   # N*s/m
    seat_rot_k: float = 32000.0      # N*m/rad (seat structure pitch stiffness)
    seat_rot_c: float = 650.0        # N*m*s/rad
    
    # Cushion & Backrest Viscoelastic 3-Phase Contact Mechanics
    cushion_k: float = 48000.0       # N/m (seat pan cushion baseline stiffness)
    cushion_c: float = 2200.0        # N*s/m
    cushion_mu: float = 0.45         # Kinetic friction coefficient on seat pan
    backrest_k: float = 28000.0      # N/m (backrest rebound support stiffness)
    backrest_c: float = 1100.0       # N*s/m
    
    # Knee - Forward Structure Obstacle Contact
    knee_clearance_mm: float = 420.0 # Forward clearance to front seat row (mm)
    knee_contact_k: float = 95000.0  # N/m
    knee_contact_c: float = 1800.0   # N*s/m
    
    # Lower Leg & Foot Contact Mechanics
    knee_joint_k: float = 4500.0     # N*m/rad (knee flexion resistance)
    knee_joint_c: float = 120.0      # N*m*s/rad
    foot_floor_k: float = 180000.0   # N/m (floor contact under foot)
    foot_floor_c: float = 3500.0     # N*s/m

class LumpedMassCrashModel:
    """Multi-DOF Inertial-Frame High-Fidelity Crash Dynamics Engine (Phase 12 Industrial MBD)."""

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
        forward_obstacle_pitch_inches: Optional[float] = None,
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
        self.forward_obstacle_pitch_inches = forward_obstacle_pitch_inches
        self.rng = np.random.default_rng(seed)

        # Flail envelope obstacle setup (if forward seat pitch is specified)
        if forward_obstacle_pitch_inches is not None and forward_obstacle_pitch_inches > 0:
            obs_x_m = float(forward_obstacle_pitch_inches * 0.0254)
            contact_cfg = FlailEnvelopeContactConfig(
                obstacles=[ObstacleSurface(position_m=(obs_x_m, 0.0, -0.20), use_soft1_stiffness=True)]
            )
            self.contact_engine = ObstacleContactEngine(contact_cfg)
        else:
            self.contact_engine = None

        # Modular Articulated Joint Kinematic Chain
        self.neck_joint = ArticulatedJoint(ArticulatedJointConfig(
            name="CERVICAL_NECK", k_rot=self.stiff.neck_rot_k, c_rot=self.stiff.neck_rot_c,
            limit_min_rad=-0.35, limit_max_rad=1.35
        ))
        self.torso_joint = ArticulatedJoint(ArticulatedJointConfig(
            name="THORACOLUMBAR_SPINE", k_rot=self.stiff.spine_rot_k, c_rot=self.stiff.spine_rot_c,
            limit_min_rad=-0.25, limit_max_rad=1.20
        ))
        self.knee_joint_l = ArticulatedJoint(ArticulatedJointConfig(
            name="KNEE_LEFT", k_rot=self.stiff.knee_joint_k, c_rot=self.stiff.knee_joint_c,
            limit_min_rad=-0.10, limit_max_rad=2.20
        ))
        self.knee_joint_r = ArticulatedJoint(ArticulatedJointConfig(
            name="KNEE_RIGHT", k_rot=self.stiff.knee_joint_k, c_rot=self.stiff.knee_joint_c,
            limit_min_rad=-0.10, limit_max_rad=2.20
        ))

    def run(self) -> dict:
        """Executes explicit time integration across the dynamic crash impact window."""
        t_arr = np.linspace(-0.010, 0.180, 1901, dtype=np.float64)
        n_steps = len(t_arr)
        dt = t_arr[1] - t_arr[0]
        g_val = 9.80665

        # Compound Orientations
        total_yaw_deg = self.yaw_deg + self.dummy_yaw_deg + self.seat_yaw_mount_deg
        total_pitch_deg = self.pitch_deg + self.seat_pitch_warp_deg
        total_roll_deg = self.roll_deg + self.seat_roll_warp_deg

        # AS8049E Pre-test 10-deg Track Warpage Initial Anchor Transformation
        R_warp = compute_euler_rotation_matrix(self.seat_yaw_mount_deg, self.seat_pitch_warp_deg, self.seat_roll_warp_deg)
        warp_z_offset_m = float(0.25 * np.sin(np.radians(abs(self.seat_pitch_warp_deg))))

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

        # Kinematic Displacement Histories
        sled_disp_x = np.zeros(n_steps, dtype=np.float64)
        sled_disp_y = np.zeros(n_steps, dtype=np.float64)
        sled_disp_z = np.zeros(n_steps, dtype=np.float64)

        # Relative Displacements
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

        # State Variables
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

        yaw_rad = np.radians(total_yaw_deg)
        is_vertical_test = "14G" in self.pulse_type or "DOWN" in self.pulse_type or "VERT" in self.pulse_type

        seat_mass = 18.0
        seat_inertia_y = 1.35

        effective_thorax_mass = self.occ.thorax_mass + self.occ.arms_mass

        pelvis_x_offset_m = self.dummy_offset_x * 0.01
        pelvis_y_offset_m = self.dummy_offset_y * 0.01
        pelvis_z_offset_m = self.dummy_offset_z * 0.01 + warp_z_offset_m

        base_slack_m = (self.stiff.belt_slack_mm + self.stiff.belt_film_spool_mm) / 1000.0
        slack_lap_eff = max(0.005, base_slack_m + pelvis_z_offset_m)
        slack_shoulder_eff = max(0.005, base_slack_m + pelvis_z_offset_m + 0.35 * np.sin(max(0.0, recline_init_rad)))

        seat_mounting = SeatMountingCompliance(
            seat_mass_kg=seat_mass,
            mount_stiffness_n_per_m=self.stiff.rail_mount_k,
            mount_damping_ns_per_m=self.stiff.rail_mount_c
        )
        seatback_engine = SeatStructureCompliance(
            seatback_rotational_k_nm_per_rad=self.stiff.seat_rot_k,
            seatback_rotational_c_nms_per_rad=self.stiff.seat_rot_c,
            inertia_kg_m2=seat_inertia_y
        )
        
        initial_settling_m = CushionSettlingMechanics.compute_initial_settling(
            occupant_mass_kg=(self.occ.pelvis_mass + 0.65 * effective_thorax_mass),
            cushion_stiffness_n_per_m=self.stiff.cushion_k
        )
        
        z_pelvis = initial_settling_m + pelvis_z_offset_m
        z_torso = initial_settling_m + pelvis_z_offset_m
        z_head = initial_settling_m + pelvis_z_offset_m

        for i in range(n_steps):
            # 0. CFL Adaptive Critical Timestep Evaluation (OpenRadioss Courant Stability)
            k_eff_est = max(self.stiff.cushion_k * 3.5, self.stiff.rail_mount_k)
            m_eff_est = (seat_mass * self.occ.pelvis_mass) / (seat_mass + self.occ.pelvis_mass)
            dt_crit = ConstitutiveModels.compute_critical_timestep(m_eff_est, k_eff_est, tssfac=0.70)
            dt_step = min(dt, dt_crit)

            # 1. Sled Kinematics
            ax_in = float(ax_sled[i])
            ay_in = float(ay_sled[i])
            az_in = float(az_sled[i])

            vx_sled += ax_in * dt_step; x_sled += vx_sled * dt_step
            vy_sled += ay_in * dt_step; y_sled += vy_sled * dt_step
            vz_sled += az_in * dt_step; z_sled += vz_sled * dt_step

            sled_disp_x[i] = float(x_sled)
            sled_disp_y[i] = float(y_sled)
            sled_disp_z[i] = float(z_sled)

            sled_mag_g = np.sqrt(ax_in**2 + ay_in**2 + az_in**2) / g_val
            sled_accel_g[i] = float(sled_mag_g)

            if is_vertical_test:
                # =========================================================================
                # 14G DOWNWARD VERTICAL DROP TEST
                # =========================================================================
                delta_z_cushion = max(0.0, z_seat - z_pelvis + initial_settling_m)
                v_rel_z_cushion = vz_seat - vz_pelvis
                f_cushion_z = ConstitutiveModels.cushion_3phase_foam(
                    penetration_m=delta_z_cushion,
                    velocity_mps=v_rel_z_cushion,
                    k_cushion=self.stiff.cushion_k,
                    c_cushion=self.stiff.cushion_c,
                    plateau_start_m=0.025,
                    densification_start_m=0.065,
                    unloading_factor=0.25
                )

                delta_z_spine = z_pelvis - z_torso
                v_rel_z_spine = vz_pelvis - vz_torso
                f_spine_z = self.stiff.spine_k_z * delta_z_spine + self.stiff.spine_c_z * v_rel_z_spine

                delta_z_neck = z_torso - z_head
                v_rel_z_neck = vz_torso - vz_head
                f_neck_z = self.stiff.neck_k_z * delta_z_neck + self.stiff.neck_c_z * v_rel_z_neck

                f_mount_z = self.stiff.rail_mount_k * (z_sled - z_seat) + self.stiff.rail_mount_c * (vz_sled - vz_seat)
                f_floor_sub_z = self.stiff.floor_elastic_k * (z_sled - z_seat) * 0.15

                f_seat_net_z = f_mount_z + f_floor_sub_z - f_cushion_z + seat_mass * g_val
                a_seat_z = f_seat_net_z / seat_mass
                vz_seat += a_seat_z * dt; z_seat += vz_seat * dt

                f_pelvis_net_z = f_cushion_z - f_spine_z + self.occ.pelvis_mass * g_val
                a_pelvis_z = f_pelvis_net_z / self.occ.pelvis_mass
                vz_pelvis += a_pelvis_z * dt; z_pelvis += vz_pelvis * dt

                f_torso_net_z = f_spine_z - f_neck_z + effective_thorax_mass * g_val
                a_torso_z = f_torso_net_z / effective_thorax_mass
                vz_torso += a_torso_z * dt; z_torso += vz_torso * dt

                f_head_net_z = f_neck_z + self.occ.head_mass * g_val
                a_head_z = f_head_net_z / self.occ.head_mass
                vz_head += a_head_z * dt; z_head += vz_head * dt

                # Relative Displacements
                seat_rel_z[i] = float(z_seat - z_sled)
                pelvis_rel_z[i] = float(z_pelvis - z_seat)
                torso_rel_z[i] = float(z_torso - z_seat)
                head_rel_z[i] = float(z_head - z_seat)

                a_meas_z = a_head_z - g_val
                head_res_g = abs(a_meas_z) / g_val
                head_accel_g[i] = float(head_res_g)

                lumbar_load_kn[i] = float(abs(f_spine_z) / 1000.0)
                neck_fz_n[i] = float(abs(f_neck_z))
                neck_moment_my[i] = float(abs(f_neck_z) * 0.022)

                femur_dynamic_n = 0.5 * (0.35 * f_cushion_z + 0.20 * abs(f_spine_z))
                femur_left_kn[i] = float(femur_dynamic_n / 1000.0)
                femur_right_kn[i] = float(femur_dynamic_n / 1000.0)

                cushion_force_n[i] = float(f_cushion_z)
                cushion_pen_mm[i] = float(delta_z_cushion * 1000.0)
                seat_sled_error_mm[i] = float(abs(z_seat - z_sled) * 1000.0)

            else:
                # =========================================================================
                # 16G FORWARD LONGITUDINAL IMPACT (3D Restraint + Industrial MBD Chain)
                # =========================================================================
                ext_lap = max(0.0, (x_seat - x_pelvis) - slack_lap_eff)
                v_rel_lap = vx_seat - vx_pelvis
                t_lap = ConstitutiveModels.nonlinear_belt_webbing(
                    extension_m=ext_lap,
                    velocity_mps=v_rel_lap,
                    k_base=self.stiff.belt_k_lap,
                    c_viscous=self.stiff.belt_c_lap,
                    ref_length_m=0.35
                )

                ext_shoulder = max(0.0, (x_seat - x_torso) - slack_shoulder_eff)
                v_rel_shoulder = vx_seat - vx_torso
                t_shoulder = ConstitutiveModels.nonlinear_belt_webbing(
                    extension_m=ext_shoulder,
                    velocity_mps=v_rel_shoulder,
                    k_base=self.stiff.belt_k_shoulder,
                    c_viscous=self.stiff.belt_c_shoulder,
                    ref_length_m=0.65
                )

                # 3D Restraint Force Vector Decomposition
                body_torso_pos = (x_torso, y_torso, z_torso)
                body_pelvis_pos = (x_pelvis, y_pelvis, z_pelvis)
                f_sh_x, f_sh_y, f_sh_z = ConstitutiveModels.resolve_belt_force_3d(
                    t_shoulder, body_torso_pos, self.stiff.belt_anchors.d_ring_xyz
                )
                f_lap_x, f_lap_y, f_lap_z = ConstitutiveModels.resolve_belt_force_3d(
                    t_lap, body_pelvis_pos, self.stiff.belt_anchors.buckle_xyz
                )

                f_belt_pelvis = t_lap
                f_belt_torso = t_shoulder

                # 2. Backrest Rebound Unilateral Contact
                pen_backrest = max(0.0, (x_seat - x_torso))
                v_pen_backrest = max(0.0, (vx_seat - vx_torso))
                f_backrest = (self.stiff.backrest_k * pen_backrest + self.stiff.backrest_c * v_pen_backrest) if pen_backrest > 0 else 0.0

                # 3. Cushion Vertical Deflection & Dynamic Friction
                delta_z_cushion = max(0.0, z_seat - z_pelvis + initial_settling_m)
                v_rel_z_cushion = vz_seat - vz_pelvis
                f_cushion_z = ConstitutiveModels.cushion_3phase_foam(
                    penetration_m=delta_z_cushion,
                    velocity_mps=v_rel_z_cushion,
                    k_cushion=self.stiff.cushion_k,
                    c_cushion=self.stiff.cushion_c,
                    unloading_factor=0.30
                )
                
                f_normal_effective = max(10.0, f_cushion_z + (self.occ.pelvis_mass + 0.50 * effective_thorax_mass) * g_val)
                v_rel_seat_pelvis = vx_seat - vx_pelvis
                f_cush_fric = self.stiff.cushion_mu * f_normal_effective * np.tanh(v_rel_seat_pelvis / 0.05)

                # 4. Inter-Segment Joint Reactions
                dx_spine = x_pelvis - x_torso
                vx_spine = vx_pelvis - vx_torso
                f_spine_x = self.stiff.spine_k_x * dx_spine + self.stiff.spine_c_x * vx_spine

                delta_z_spine = z_pelvis - z_torso
                vz_spine = vz_pelvis - vz_torso
                f_spine_z = self.stiff.spine_k_z * delta_z_spine + self.stiff.spine_c_z * vz_spine

                dx_neck = x_torso - x_head
                vx_neck = vx_torso - vx_head
                neck_whiplash_gamma = 1.0 + 15.0 * (max(0.0, abs(dx_neck) - 0.035) ** 1.5)
                f_neck_x = (self.stiff.neck_k_x * neck_whiplash_gamma) * dx_neck + self.stiff.neck_c_x * vx_neck

                delta_z_neck = z_torso - z_head
                vz_neck = vz_torso - vz_head
                f_neck_z = self.stiff.neck_k_z * delta_z_neck + self.stiff.neck_c_z * vz_neck

                f_neck_y = self.stiff.neck_k_x * 0.8 * (y_seat - y_head) + self.stiff.neck_c_x * (vy_seat - vy_head)

                # 5. Secondary Head Strike Flail Envelope Contact (LS-DYNA SOFT=1 Formulated in Cabin Frame)
                f_head_contact_x = 0.0; f_head_contact_y = 0.0; f_head_contact_z = 0.0
                if self.contact_engine is not None:
                    head_cg_x = (x_seat - x_head) + 0.54 - self.contact_engine.config.head_radius_m
                    head_cg_cabin = (head_cg_x, y_head - y_seat, z_head - z_seat)
                    head_vel_cabin = (vx_seat - vx_head, vy_seat - vy_head, vz_seat - vz_head)
                    f_head_contact_x, f_head_contact_y, f_head_contact_z, pen_obs, has_contact = self.contact_engine.evaluate_head_contact(
                        head_cg_cabin, head_vel_cabin, head_mass_kg=self.occ.head_mass, dt_s=dt
                    )

                # 6. Rail Mount Track Dynamics
                f_occupant_reaction_x = f_belt_pelvis + f_belt_torso + f_cush_fric - f_backrest + abs(f_head_contact_x)
                a_seat_x = seat_mounting.evaluate_seat_acceleration(ax_in, vx_sled, x_sled, f_occupant_reaction_x, dt)
                x_seat = seat_mounting.x_seat
                vx_seat = seat_mounting.v_seat

                f_mount_y = self.stiff.rail_mount_k * (y_sled - y_seat) + self.stiff.rail_mount_c * (vy_sled - vy_seat)
                a_seat_y = f_mount_y / seat_mass
                vy_seat += a_seat_y * dt; y_seat += vy_seat * dt

                f_mount_z = self.stiff.rail_mount_k * (z_sled - z_seat) + self.stiff.rail_mount_c * (vz_sled - vz_seat)
                a_seat_z = (f_mount_z - f_cushion_z + seat_mass * g_val) / seat_mass
                vz_seat += a_seat_z * dt; z_seat += vz_seat * dt

                # 7. Equations of Motion in Inertial Global Frame
                f_pelvis_net_x = f_belt_pelvis + f_cush_fric - f_spine_x
                a_pelvis_x = f_pelvis_net_x / self.occ.pelvis_mass
                vx_pelvis += a_pelvis_x * dt; x_pelvis += vx_pelvis * dt

                f_pelvis_net_z = f_cushion_z - f_spine_z + self.occ.pelvis_mass * g_val + f_belt_pelvis * 0.25
                a_pelvis_z = f_pelvis_net_z / self.occ.pelvis_mass
                vz_pelvis += a_pelvis_z * dt; z_pelvis += vz_pelvis * dt

                f_torso_net_x = f_belt_torso + f_spine_x + f_backrest - f_neck_x
                a_torso_x = f_torso_net_x / effective_thorax_mass
                vx_torso += a_torso_x * dt; x_torso += vx_torso * dt

                f_torso_net_z = f_spine_z - f_neck_z + effective_thorax_mass * g_val - f_belt_torso * 0.15
                a_torso_z = f_torso_net_z / effective_thorax_mass
                vz_torso += a_torso_z * dt; z_torso += vz_torso * dt

                f_head_net_x = f_neck_x - f_head_contact_x
                a_head_x = f_head_net_x / self.occ.head_mass
                vx_head += a_head_x * dt; x_head += vx_head * dt

                a_head_y = (f_neck_y - f_head_contact_y) / self.occ.head_mass
                vy_head += a_head_y * dt; y_head += vy_head * dt

                f_head_net_z = f_neck_z - f_head_contact_z + self.occ.head_mass * g_val
                a_head_z = f_head_net_z / self.occ.head_mass
                vz_head += a_head_z * dt; z_head += vz_head * dt

                # 8. Rotational Dynamics via Modular Articulated Joints
                m_seat_applied = (f_belt_torso * 0.45 + f_belt_pelvis * 0.15)
                theta_seat, m_seat_restoring = seatback_engine.evaluate_seatback_response(
                    torso_rebound_moment_nm=m_seat_applied, dt=dt
                )
                theta_seat = max(-0.15, min(0.45, theta_seat))
                seatback_engine.seatback_angle_rad = theta_seat
                omega_seat = seatback_engine.seatback_omega_rad_per_s

                # Torso Joint Reaction Moment
                m_spine_restoring, _ = self.torso_joint.compute_restoring_moment(theta_torso, omega_torso)
                m_torso_pitch = (effective_thorax_mass * a_torso_x * 0.22) - (f_belt_torso * 0.35 + m_spine_restoring)
                alpha_torso = m_torso_pitch / self.occ.torso_inertia_y
                omega_torso += alpha_torso * dt
                theta_torso = max(-0.25, min(1.20, theta_torso + omega_torso * dt))

                # Neck Joint Reaction Moment
                m_neck_restoring, _ = self.neck_joint.compute_restoring_moment(theta_head, omega_head)
                m_head_pitch = (self.occ.head_mass * abs(a_head_x - a_torso_x) * self.occ.neck_length_m) - m_neck_restoring
                alpha_head = m_head_pitch / self.occ.head_inertia_y
                omega_head += alpha_head * dt
                theta_head = max(-0.35, min(1.35, theta_head + omega_head * dt))

                # 9. Femurs & Knee Multi-Body Kinematics
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

                # Record Displacements
                seat_deflection_mm[i] = float(abs(x_seat - x_sled) * 1000.0)
                seat_rel_x[i] = float(x_seat - x_sled)
                seat_rel_y[i] = float(y_seat - y_sled)
                seat_rel_z[i] = float(z_seat - z_sled)
                seat_pitch_rad[i] = float(theta_seat)

                pelvis_rel_x[i] = float(x_seat - x_pelvis)
                pelvis_rel_z[i] = float(z_pelvis - z_seat)
                torso_rel_x[i] = float(x_seat - x_torso)
                torso_rel_z[i] = float(z_torso - z_seat)
                torso_pitch_rad[i] = float(theta_torso)

                head_rel_x[i] = float(x_seat - x_head)
                head_rel_y[i] = float(y_head - y_seat)
                head_rel_z[i] = float(z_head - z_seat)
                head_pitch_rad[i] = float(theta_head)

                # 10. Head Resultant Acceleration for HIC15
                a_head_cg_x = a_head_x + alpha_head * self.occ.neck_length_m * np.cos(theta_head)
                a_head_cg_y = a_head_y
                a_head_cg_z = a_head_z - g_val
                
                head_res_g = np.sqrt(a_head_cg_x**2 + a_head_cg_y**2 + a_head_cg_z**2) / g_val
                head_accel_g[i] = float(head_res_g)

                # 11. True Neck Injury Criterion Channels with OC Moment Transformation
                neck_axial_dynamic = abs(f_neck_z) + self.occ.head_mass * abs(a_head_x) * np.sin(abs(theta_head))
                neck_moment_cell = self.occ.head_mass * abs(a_head_x) * self.occ.neck_length_m * np.cos(theta_head) + self.occ.head_inertia_y * abs(alpha_head)
                d_oc_m = 0.01778
                neck_moment_oc = max(0.0, neck_moment_cell - d_oc_m * abs(f_neck_x) * 0.20)
                neck_moment_sign = 1.0 if theta_head >= 0 else -1.0
                
                neck_moment_my[i] = float(neck_moment_oc * neck_moment_sign)
                neck_fz_n[i] = float(neck_axial_dynamic)

                # 12. Lumbar Spinal Load
                pitch_angle_comp = np.sin(np.radians(abs(total_pitch_deg) + abs(self.dummy_recline_deg)))
                lumbar_total_n = abs(f_spine_z) + abs(f_spine_x) * pitch_angle_comp * 1.8 + effective_thorax_mass * g_val
                lumbar_load_kn[i] = float(lumbar_total_n / 1000.0)

                belt_shoulder_kn[i] = float(f_belt_torso / 1000.0)
                belt_lap_kn[i] = float(f_belt_pelvis / 1000.0)

                belt_lap_ext_mm[i] = float(ext_lap * 1000.0)
                belt_shoulder_ext_mm[i] = float(ext_shoulder * 1000.0)
                cushion_force_n[i] = float(f_cushion_z)
                cushion_pen_mm[i] = float(delta_z_cushion * 1000.0)
                backrest_force_n[i] = float(f_backrest)
                backrest_pen_mm[i] = float(pen_backrest * 1000.0)
                seat_sled_error_mm[i] = float(abs(x_seat - x_sled) * 1000.0)

                head_vec_fx[i] = float(-f_neck_x - f_head_contact_x)
                head_vec_fy[i] = float(-f_neck_y)
                head_vec_fz[i] = float(-f_neck_z)

                torso_vec_fx[i] = float(-f_sh_x - f_spine_x + f_neck_x + f_backrest)
                torso_vec_fy[i] = float(-f_sh_y)
                torso_vec_fz[i] = float(-f_sh_z - f_neck_z)

                pelvis_vec_fx[i] = float(-f_lap_x + f_spine_x - f_cush_fric)
                pelvis_vec_fy[i] = float(-f_lap_y)
                pelvis_vec_fz[i] = float(-f_lap_z + f_spine_z)

                seat_vec_fx[i] = float(f_belt_pelvis + f_belt_torso + f_cush_fric - f_backrest)

            excursion_head_mm = (abs(x_seat - x_head) + 0.54) * 1000.0 if not is_vertical_test else 540.0
            if excursion_head_mm > max_head_excursion:
                max_head_excursion = excursion_head_mm

            excursion_knee_mm = (max(abs(femur_rel_l[i]), abs(femur_rel_r[i])) + 0.41) * 1000.0 if not is_vertical_test else 410.0
            if excursion_knee_mm > max_knee_excursion:
                max_knee_excursion = excursion_knee_mm

        # Physical Submarining Kinematic Risk Model
        pelvis_rot_rad = torso_pitch_rad * 0.70
        alpha_belt_deg = np.degrees(np.arctan2(0.20, np.maximum(0.01, pelvis_rel_x))) - np.degrees(pelvis_rot_rad)
        submarining_risk_series = np.maximum(0.0, (pelvis_rel_x * np.cos(pelvis_rot_rad) - 0.040) / 0.080)
        max_submarining_risk = float(round(np.max(submarining_risk_series), 2))
        submarining_status = "ELEVATED_SUBMARINING_RISK" if (max_submarining_risk > 1.0 or np.min(alpha_belt_deg) < 30.0) else "LOW_NOMINAL"

        structural_status = "INTACT_NO_FAILURE"
        if abs(self.yaw_deg) > 40.0 or abs(self.pitch_deg) > 25.0:
            structural_status = "WARNING_STRUCTURAL_PLASTIC_DEFORMATION"

        # Signal Filtering
        filtered_head_accel = sae_j211_cfc_filter(head_accel_g, dt, cfc=1000)
        filtered_femur_l = sae_j211_cfc_filter(femur_left_kn, dt, cfc=600)
        filtered_femur_r = sae_j211_cfc_filter(femur_right_kn, dt, cfc=600)
        filtered_lumbar = sae_j211_cfc_filter(lumbar_load_kn, dt, cfc=600)
        filtered_neck_fz = sae_j211_cfc_filter(neck_fz_n, dt, cfc=1000)
        filtered_neck_my = sae_j211_cfc_filter(neck_moment_my, dt, cfc=1000)
        filtered_belt_shoulder = np.maximum(0.0, sae_j211_cfc_filter(belt_shoulder_kn, dt, cfc=600))
        filtered_belt_lap = np.maximum(0.0, sae_j211_cfc_filter(belt_lap_kn, dt, cfc=600))

        req_dv = 10.7 if is_vertical_test else 13.4
        delta_v, dv_pass = validate_pulse_delta_v(t_arr, sled_accel_g, required_delta_v=req_dv)

        max_lap_f = float(np.max(filtered_belt_lap))
        max_sh_f = float(np.max(filtered_belt_shoulder))
        max_cush_f = float(np.max(cushion_force_n)) / 1000.0
        max_back_f = float(np.max(backrest_force_n)) / 1000.0
        max_error = float(np.max(seat_sled_error_mm))
        rms_error = float(np.sqrt(np.mean(seat_sled_error_mm**2)))

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

        lap_engaged = (np.array(filtered_belt_lap) > 0.05).tolist()
        shoulder_engaged = (np.array(filtered_belt_shoulder) > 0.05).tolist()

        lap_constraint_dict = {
            "type": "NONLINEAR_LAP_BELT",
            "status": "ENGAGED" if max_lap_f > 0.1 else "DISENGAGED",
            "peak_force_kn": round(max_lap_f, 2),
            "peak_tension_kn": round(max_lap_f, 2),
            "extension_series_mm": belt_lap_ext_mm.tolist(),
            "load_series_kn": filtered_belt_lap.tolist(),
            "engaged_series": lap_engaged
        }

        shoulder_constraint_dict = {
            "type": "NONLINEAR_HARNESS_3POINT",
            "status": "ENGAGED" if max_sh_f > 0.1 else "DISENGAGED",
            "peak_force_kn": round(max_sh_f, 2),
            "peak_tension_kn": round(max_sh_f, 2),
            "extension_series_mm": belt_shoulder_ext_mm.tolist(),
            "load_series_kn": filtered_belt_shoulder.tolist(),
            "engaged_series": shoulder_engaged
        }

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
                "seat_to_dummy_lap": lap_constraint_dict,
                "lap_belt": lap_constraint_dict,
                "seat_to_dummy_shoulder": shoulder_constraint_dict,
                "shoulder_belt": shoulder_constraint_dict,
                "cushion": {
                    "type": "3PHASE_CELLULAR_FOAM_HYSTERESIS",
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
