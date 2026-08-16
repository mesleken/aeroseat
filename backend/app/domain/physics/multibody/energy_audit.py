import numpy as np

class EnergyMomentumAuditEngine:
    """Instantaneous Energy & Momentum Audit Engine for Multibody Occupant Dynamics.
    
    Audit Equation:
        E_initial_kinetic + W_external_pulse = E_current_kinetic + E_potential + E_dissipated_total
        Energy Residual Ratio R_E = |E_in - E_out - E_diss| / E_in
    """
    
    def __init__(self, initial_kinetic_energy_j: float = 0.0):
        self.e_init = float(initial_kinetic_energy_j)
        self.w_ext = 0.0
        self.e_diss_contacts = 0.0
        self.e_diss_belts = 0.0
        self.e_diss_joints = 0.0

    def update_dissipation(self, contact_diss_w: float, belt_diss_w: float, joint_diss_w: float, dt: float):
        """Accumulates dissipated energy (J) over time step dt."""
        self.e_diss_contacts += max(0.0, float(contact_diss_w * dt))
        self.e_diss_belts += max(0.0, float(belt_diss_w * dt))
        self.e_diss_joints += max(0.0, float(joint_diss_w * dt))

    def evaluate_audit(self, current_kinetic_energy_j: float, current_potential_energy_j: float) -> dict:
        """Evaluates energy balance audit and returns residual ratio."""
        e_kin = float(current_kinetic_energy_j)
        e_pot = float(current_potential_energy_j)
        e_diss_total = float(self.e_diss_contacts + self.e_diss_belts + self.e_diss_joints)
        
        e_in = float(self.e_init + self.w_ext)
        e_out = float(e_kin + e_pot + e_diss_total)
        
        denom = max(1.0, e_in)
        residual_ratio = float(abs(e_in - e_out) / denom)
        
        return {
            "initial_kinetic_energy_j": round(self.e_init, 2),
            "external_work_j": round(self.w_ext, 2),
            "current_kinetic_energy_j": round(e_kin, 2),
            "current_potential_energy_j": round(e_pot, 2),
            "dissipated_energy_contacts_j": round(self.e_diss_contacts, 2),
            "dissipated_energy_belts_j": round(self.e_diss_belts, 2),
            "dissipated_energy_joints_j": round(self.e_diss_joints, 2),
            "total_dissipated_energy_j": round(e_diss_total, 2),
            "energy_residual_ratio": round(residual_ratio, 6),
            "energy_audit_verdict": "NUMERICAL_ENERGY_BALANCE_PASS" if residual_ratio < 0.02 else "RESIDUAL_WARNING"
        }
