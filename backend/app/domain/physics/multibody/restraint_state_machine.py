import numpy as np

class RestraintSubsystemStateMachine:
    """Restraint Subsystem Finite State Machine & Absorbed Energy Engine.
    
    States:
        0: SLACK
        1: ENGAGEMENT
        2: PRETENSION
        3: ELASTIC_LOADING
        4: LOAD_LIMITING
        5: UNLOADING_HYSTERESIS
    """
    
    STATE_NAMES = {
        0: "SLACK",
        1: "ENGAGEMENT",
        2: "PRETENSION",
        3: "ELASTIC_LOADING",
        4: "LOAD_LIMITING",
        5: "UNLOADING_HYSTERESIS"
    }

    def __init__(
        self,
        slack_m: float = 0.015,
        load_limit_n: float = 6000.0,
        webbing_stiffness_n_per_m: float = 120000.0
    ):
        self.slack = float(slack_m)
        self.load_limit = float(load_limit_n)
        self.k_webbing = float(webbing_stiffness_n_per_m)
        
        self.current_state_code = 0
        self.max_extension_m = 0.0
        self.absorbed_energy_j = 0.0

    def update_state(self, current_extension_m: float, extension_vel_m_per_s: float, tension_n: float, dt: float) -> str:
        """Updates restraint state machine, computes absorbed hysteresis energy, and returns state name."""
        ext = float(current_extension_m)
        v_ext = float(extension_vel_m_per_s)
        t_n = float(tension_n)
        
        if ext <= 0.0:
            self.current_state_code = 0 # SLACK
        elif v_ext < 0.0:
            self.current_state_code = 5 # UNLOADING_HYSTERESIS
        elif t_n >= self.load_limit:
            self.current_state_code = 4 # LOAD_LIMITING
            # Accumulate plastic yield work done by load limiter
            self.absorbed_energy_j += float(t_n * max(0.0, v_ext) * dt)
        elif ext > 0.0 and t_n > 0.0:
            self.current_state_code = 3 # ELASTIC_LOADING
        else:
            self.current_state_code = 1 # ENGAGEMENT
            
        if ext > self.max_extension_m:
            self.max_extension_m = ext
            
        return self.STATE_NAMES[self.current_state_code]

    def get_audit(self) -> dict:
        """Returns restraint state audit and total absorbed energy."""
        return {
            "current_belt_state": self.STATE_NAMES[self.current_state_code],
            "max_belt_extension_mm": round(self.max_extension_m * 1000.0, 2),
            "absorbed_load_limiter_energy_j": round(self.absorbed_energy_j, 2)
        }
