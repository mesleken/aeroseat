import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List
from app.domain.physics.multibody.constitutive import ConstitutiveModels

@dataclass
class ObstacleSurface:
    """Defines a planar barrier in the cabin (e.g., front seat backrest, tray table, bulkhead)."""
    name: str = "FRONT_SEAT_BACKREST"
    position_m: tuple[float, float, float] = (0.8128, 0.0, -0.20) # 32 inch seat pitch (0.8128 m)
    normal_vector: tuple[float, float, float] = (-1.0, 0.0, 0.0) # Points back towards occupant
    k_contact: float = 185000.0   # N/m (calibrated from FAA headform drop test 15-25 J)
    c_contact: float = 2400.0     # N*s/m
    exponent: float = 1.5         # Hertzian contact parameter
    width_m: float = 0.50
    height_m: float = 0.60
    effective_mass_kg: float = 15.0 # Effective inertia of front seat / obstacle
    use_soft1_stiffness: bool = True

@dataclass
class FlailEnvelopeContactConfig:
    """Configures cabin obstacles and contact detection parameters."""
    head_radius_m: float = 0.0813  # FAA Hybrid III 50th percentile male headform radius (~81.3 mm)
    knee_radius_m: float = 0.0650
    obstacles: List[ObstacleSurface] = field(default_factory=lambda: [ObstacleSurface()])

class ObstacleContactEngine:
    """
    Head & Knee Strike Flail Envelope Contact Detection Engine per FAA 14 CFR § 25.562 / LS-DYNA SOFT=1.
    Calculates 3D impact forces when occupant segments penetrate surrounding cabin obstacles.
    """

    def __init__(self, config: Optional[FlailEnvelopeContactConfig] = None):
        self.config = config or FlailEnvelopeContactConfig()

    def evaluate_head_contact(
        self,
        head_cg_pos_m: tuple[float, float, float] | np.ndarray,
        head_vel_mps: tuple[float, float, float] | np.ndarray,
        head_mass_kg: float = 4.54,
        dt_s: float = 0.0001
    ) -> tuple[float, float, float, float, bool]:
        """
        Evaluates penetration against cabin obstacles.
        Returns (Fx, Fy, Fz, penetration_m, is_contacting).
        """
        r_head = np.array(head_cg_pos_m, dtype=np.float64)
        v_head = np.array(head_vel_mps, dtype=np.float64)
        r_radius = self.config.head_radius_m

        total_f = np.zeros(3, dtype=np.float64)
        max_penetration = 0.0
        contact_active = False

        for obs in self.config.obstacles:
            n_vec = np.array(obs.normal_vector, dtype=np.float64)
            n_norm = np.linalg.norm(n_vec)
            if n_norm < 1e-6:
                continue
            n_unit = n_vec / n_norm
            r_obs = np.array(obs.position_m, dtype=np.float64)
            
            # Check 2D bounding window (lateral Y and vertical Z)
            dy = abs(r_head[1] - r_obs[1])
            dz = abs(r_head[2] - r_obs[2])
            if dy > (obs.width_m / 2.0 + r_radius) or dz > (obs.height_m / 2.0 + r_radius):
                continue
            
            # Plane penetration depth
            dist_to_plane = np.dot(r_head - r_obs, -n_unit) + r_radius
            
            if dist_to_plane > 0.0:
                contact_active = True
                penetration = dist_to_plane
                if penetration > max_penetration:
                    max_penetration = penetration
                
                v_normal = np.dot(v_head, -n_unit)
                
                # Determine contact stiffness (LS-DYNA SOFT=1 formulation with calibrated FAA barrier bounds)
                if obs.use_soft1_stiffness:
                    k_soft1 = ConstitutiveModels.compute_soft1_contact_stiffness(
                        m1_kg=head_mass_kg,
                        m2_kg=obs.effective_mass_kg,
                        dt_s=dt_s,
                        sofscl=0.005
                    )
                    k_effective = max(obs.k_contact * 0.5, min(obs.k_contact * 2.0, k_soft1))
                    c_effective = obs.c_contact
                else:
                    k_effective = obs.k_contact
                    c_effective = obs.c_contact

                # Hunt-Crossley non-linear contact force
                f_mag = ConstitutiveModels.hunt_crossley_joint(
                    delta_m=penetration,
                    velocity_mps=v_normal,
                    k_joint=k_effective,
                    c_joint=c_effective,
                    exponent=obs.exponent
                )
                
                total_f += f_mag * n_unit

        return float(total_f[0]), float(total_f[1]), float(total_f[2]), float(max_penetration), contact_active
