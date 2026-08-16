import numpy as np

class ArticulatedJoint:
    """Non-linear Articulated Biomechanical Joint Segment (Cervical / Lumbar / Hip / Knee).
    
    Includes:
    - Non-linear elastic rotational stiffness M_elastic(theta)
    - Rate-dependent viscous damping M_viscous(omega)
    - Anatomical Range of Motion (ROM) hard stops
    """
    
    def __init__(
        self,
        name: str,
        rotational_k_nm_per_rad: float,
        rotational_c_nms_per_rad: float,
        rom_min_rad: float,
        rom_max_rad: float,
        hardening_exponent: float = 2.0
    ):
        self.name = str(name)
        self.k_rot = float(rotational_k_nm_per_rad)
        self.c_rot = float(rotational_c_nms_per_rad)
        self.rom_min = float(rom_min_rad)
        self.rom_max = float(rom_max_rad)
        self.exponent = float(hardening_exponent)

    def evaluate_restoring_torque(self, relative_angle_rad: float, relative_omega_rad_per_s: float) -> tuple[float, float]:
        """Evaluates joint restoring torque (Nm) and dissipated energy rate (W).
        
        Returns:
            (torque_nm, dissipation_rate_w)
        """
        theta = float(relative_angle_rad)
        omega = float(relative_omega_rad_per_s)
        
        # 1. Non-linear Elastic Torque
        m_elastic = self.k_rot * theta
        
        # Progressive ROM limit hardening near anatomical boundaries
        if theta > self.rom_max:
            excess = theta - self.rom_max
            m_elastic += self.k_rot * 15.0 * (excess ** self.exponent)
        elif theta < self.rom_min:
            excess = self.rom_min - theta
            m_elastic -= self.k_rot * 15.0 * (excess ** self.exponent)
        
        # 2. Viscous Damping Torque
        m_viscous = self.c_rot * omega
        
        m_total = m_elastic + m_viscous
        dissipation_rate = self.c_rot * (omega ** 2)
        
        return float(m_total), float(dissipation_rate)

class CervicalJoint(ArticulatedJoint):
    """Cervical Spine Joint with Flexion/Extension Whiplash Hardening and Nij Load Coupling."""
    
    def __init__(self):
        super().__init__(
            name="Cervical_Joint",
            rotational_k_nm_per_rad=18.5,
            rotational_c_nms_per_rad=0.45,
            rom_min_rad=-0.35, # Extension limit (-20 deg)
            rom_max_rad=1.20   # Flexion limit (+68 deg)
        )

class LumbarJoint(ArticulatedJoint):
    """Lumbar Vertebral Column Joint with High Compression & Pitch Bending Stiffness."""
    
    def __init__(self):
        super().__init__(
            name="Lumbar_Joint",
            rotational_k_nm_per_rad=85.0,
            rotational_c_nms_per_rad=1.85,
            rom_min_rad=-0.25,
            rom_max_rad=0.85
        )
