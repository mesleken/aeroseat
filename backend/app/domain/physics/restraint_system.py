import numpy as np

class RestraintSystem:
    """3D Vector Line-of-Action Restraint Engine with Pretensioner & Load Limiter.
    
    Models:
    - 3D Anchor Geometry to Occupant Nodes (Force Vector F = T * e_hat, Torque M = r x F)
    - Webbing Non-linear Elasticity & Slack
    - Pyrotechnic Pretensioner F_pretensioner(t)
    - Constant-Force Load Limiter F_limit plateau
    """
    
    def __init__(
        self,
        stiffness_n_per_m: float = 120000.0,
        damping_ns_per_m: float = 800.0,
        slack_m: float = 0.015,
        pretensioner_active: bool = True,
        pretensioner_fire_ms: float = 10.0,
        pretensioner_pull_m: float = 0.030,
        load_limiter_active: bool = True,
        load_limiter_threshold_n: float = 6000.0
    ):
        self.k_belt = float(stiffness_n_per_m)
        self.c_belt = float(damping_ns_per_m)
        self.slack_m = float(slack_m)
        self.pretensioner_active = pretensioner_active
        self.pretensioner_fire_ms = float(pretensioner_fire_ms)
        self.pretensioner_pull_m = float(pretensioner_pull_m)
        self.load_limiter_active = load_limiter_active
        self.load_limiter_threshold_n = float(load_limiter_threshold_n)

    def compute_pretension_stroke(self, time_s: float) -> float:
        """Computes pyrotechnic pretensioner stroke reduction (m) over time."""
        if not self.pretensioner_active:
            return 0.0
        time_ms = time_s * 1000.0
        if time_ms < self.pretensioner_fire_ms:
            return 0.0
        
        # 15 ms smooth cosine stroke ramp
        elapsed_ms = time_ms - self.pretensioner_fire_ms
        if elapsed_ms >= 15.0:
            return self.pretensioner_pull_m
        
        fraction = 0.5 * (1.0 - np.cos(np.pi * elapsed_ms / 15.0))
        return self.pretensioner_pull_m * fraction

    def evaluate_belt_tension(
        self,
        anchor_pos: np.ndarray,
        node_pos: np.ndarray,
        node_vel: np.ndarray,
        initial_length_m: float,
        time_s: float
    ) -> tuple[float, np.ndarray, float]:
        """Evaluates scalar belt tension (N), 3D force vector on node (N), and stroke extension (m).
        
        Returns:
            (tension_n, force_vec_n, extension_m)
        """
        vec = anchor_pos - node_pos
        current_len = float(np.linalg.norm(vec))
        if current_len < 1e-6:
            return 0.0, np.zeros(3), 0.0
        
        e_hat = vec / current_len # Unit vector pointing from occupant node toward anchor
        
        # Effective slack taking pretensioner stroke into account
        pretension_stroke = self.compute_pretension_stroke(time_s)
        effective_slack = max(0.0, self.slack_m - pretension_stroke)
        
        extension = current_len - initial_length_m + pretension_stroke
        net_extension = extension - effective_slack
        
        if net_extension <= 0.0:
            return 0.0, np.zeros(3), 0.0
        
        # Relative velocity along line of action
        v_rel = float(np.dot(node_vel, -e_hat)) # Velocity away from anchor
        
        raw_tension = self.k_belt * net_extension + self.c_belt * max(0.0, v_rel)
        raw_tension = max(0.0, raw_tension)
        
        # Apply Constant-Force Load Limiter plateau
        if self.load_limiter_active and raw_tension > self.load_limiter_threshold_n:
            final_tension = self.load_limiter_threshold_n
        else:
            final_tension = raw_tension
        
        force_vec = final_tension * e_hat
        return float(final_tension), force_vec, float(net_extension)
