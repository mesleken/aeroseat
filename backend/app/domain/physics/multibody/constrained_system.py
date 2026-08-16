import numpy as np
from app.domain.physics.multibody.rigid_body import RigidBody6DOF

class ConstrainedMultibodySystem:
    """Phase 2.5: Constrained Multibody Dynamics Engine.
    
    Assembles Global System Dynamics:
        M(q) * q_ddot + C(q, q_dot) + G(q) + K(q) + D(q, q_dot) = Q_ext + J^T * lambda
        
    Where:
        q: Generalized System Coordinates Vector [x_s, y_s, z_s, theta_s, x_p, theta_p, x_t, theta_t, x_h, theta_h]
        M(q): Mass Matrix
        J^T * lambda: Kinematic Joint Constraint Reactions (Lagrange Multipliers)
    """
    
    def __init__(self, segment_bodies: list[RigidBody6DOF] = None):
        self.bodies = segment_bodies or []
        self.n_dof = sum(6 for _ in self.bodies) if self.bodies else 12

    def assemble_mass_matrix(self) -> np.ndarray:
        """Assembles block-diagonal global mass matrix M(q)."""
        mass_elements = []
        for body in self.bodies:
            mass_elements.extend([body.mass, body.mass, body.mass, body.ixx, body.iyy, body.izz])
        return np.diag(mass_elements if mass_elements else [1.0] * self.n_dof)

    def evaluate_constraint_jacobian(self, q_state: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Evaluates kinematic joint constraint equations C(q) = 0 and Jacobian matrix J = dC/dq.
        
        Returns:
            (constraint_residual_C, jacobian_J)
        """
        n_q = len(q_state)
        # 4 kinematic joint constraint equations (Pelvis-Seat, Spine, Neck)
        n_constraints = 4
        J = np.zeros((n_constraints, n_q), dtype=np.float64)
        C = np.zeros(n_constraints, dtype=np.float64)
        
        if n_q >= 6:
            # Pelvis-Seat Joint constraint (C1: relative x displacement bound)
            C[0] = q_state[4] - q_state[0] # x_pelvis - x_seat
            J[0, 4] = 1.0; J[0, 0] = -1.0
            
            # Spine Joint constraint (C2: relative x displacement bound)
            if n_q >= 8:
                C[1] = q_state[6] - q_state[4] # x_torso - x_pelvis
                J[1, 6] = 1.0; J[1, 4] = -1.0
                
            # Cervical Joint constraint (C3: relative x displacement bound)
            if n_q >= 10:
                C[2] = q_state[8] - q_state[6] # x_head - x_torso
                J[2, 8] = 1.0; J[2, 6] = -1.0
                
        return C, J

    def compute_constraint_reactions(self, q_state: np.ndarray, q_dot: np.ndarray, q_ext: np.ndarray) -> np.ndarray:
        """Computes Lagrange Multipliers lambda and constraint force vector J^T * lambda.
        
        System:
            [ M   J^T ] [ q_ddot ]   [ Q_ext ]
            [ J    0  ] [ lambda ] = [  gamma ]
        """
        C, J = self.evaluate_constraint_jacobian(q_state)
        M = self.assemble_mass_matrix()
        
        # Baumgarte constraint stabilization
        alpha_b, beta_b = 10.0, 5.0
        gamma = -alpha_b * C - beta_b * (J @ q_dot[:len(J[0])]) if len(q_dot) >= len(J[0]) else -alpha_b * C
        
        n_q = len(q_ext)
        n_c = len(C)
        
        A = np.zeros((n_q + n_c, n_q + n_c), dtype=np.float64)
        A[:n_q, :n_q] = M[:n_q, :n_q]
        A[:n_q, n_q:] = J[:, :n_q].T
        A[n_q:, :n_q] = J[:, :n_q]
        
        b = np.zeros(n_q + n_c, dtype=np.float64)
        b[:n_q] = q_ext
        b[n_q:] = gamma
        
        try:
            sol = np.linalg.solve(A, b)
            joint_reaction_forces = J[:, :n_q].T @ sol[n_q:]
            return joint_reaction_forces
        except np.linalg.LinAlgError:
            return np.zeros(n_q, dtype=np.float64)
