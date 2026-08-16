import numpy as np

class RigidBody6DOF:
    """Newton-Euler 6-Degrees of Freedom Rigid Body Dynamics Segment.
    
    States:
        Position x = [x, y, z]^T (m)
        Velocity v = [vx, vy, vz]^T (m/s)
        Euler Angles theta = [phi, theta, psi]^T (rad: roll, pitch, yaw)
        Angular Velocity omega = [wx, wy, wz]^T (rad/s)
        
    Equations of Motion:
        m * dv/dt = sum(F)
        I * d(omega)/dt + omega x (I * omega) = sum(M)
    """
    
    def __init__(
        self,
        name: str,
        mass_kg: float,
        inertia_kgm2: tuple[float, float, float],
        initial_pos: np.ndarray = None,
        initial_rot: np.ndarray = None
    ):
        self.name = str(name)
        self.mass = float(mass_kg)
        self.ixx, self.iyy, self.izz = [float(v) for v in inertia_kgm2]
        self.inertia_matrix = np.diag([self.ixx, self.iyy, self.izz])
        
        self.pos = np.array(initial_pos if initial_pos is not None else [0.0, 0.0, 0.0], dtype=np.float64)
        self.vel = np.zeros(3, dtype=np.float64)
        self.accel = np.zeros(3, dtype=np.float64)
        
        self.rot = np.array(initial_rot if initial_rot is not None else [0.0, 0.0, 0.0], dtype=np.float64)
        self.omega = np.zeros(3, dtype=np.float64)
        self.alpha = np.zeros(3, dtype=np.float64)

    def evaluate_derivatives(self, force_sum_n: np.ndarray, moment_sum_nm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Evaluates linear acceleration dv/dt and angular acceleration d(omega)/dt.
        
        Translational:
            a = F_sum / m
            
        Rotational (Euler Rotational Gyroscopic Equations):
            I * alpha + omega x (I * omega) = M_sum
            alpha = I^-1 * (M_sum - omega x (I * omega))
        """
        a_lin = force_sum_n / self.mass
        
        gyro = np.cross(self.omega, self.inertia_matrix @ self.omega)
        net_moment = moment_sum_nm - gyro
        
        inv_inertia = np.diag([1.0 / self.ixx, 1.0 / self.iyy, 1.0 / self.izz])
        a_ang = inv_inertia @ net_moment
        
        return a_lin, a_ang

    def integrate_rk4_step(self, force_sum_n: np.ndarray, moment_sum_nm: np.ndarray, dt: float):
        """Integrates 6-DOF state by one time step dt via Explicit RK4 scheme."""
        a_lin, a_ang = self.evaluate_derivatives(force_sum_n, moment_sum_nm)
        
        self.accel = a_lin
        self.alpha = a_ang
        
        self.vel += a_lin * dt
        self.pos += self.vel * dt
        
        self.omega += a_ang * dt
        self.rot += self.omega * dt

    def compute_kinetic_energy(self) -> float:
        """Computes total translational + rotational kinetic energy (J)."""
        ke_trans = 0.5 * self.mass * float(np.dot(self.vel, self.vel))
        ke_rot = 0.5 * float(np.dot(self.omega, self.inertia_matrix @ self.omega))
        return ke_trans + ke_rot
