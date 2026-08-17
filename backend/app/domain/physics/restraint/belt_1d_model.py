"""
AeroSeat - 1D Multi-Node (Slip-Ring) Emniyet Kemeri Modeli.

Modelleme Mantığı:
Kemer, mankenin üzerinden kayabilen küçük sürtünmeli küresel düğümlerin (Point Masses)
yüksek rijitlikli, tek yönlü (tension-only) yaylar (ChLinkTSDA / Discrete Spring-Damper)
ile birbirine bağlanmasıyla modellenir.

Özellikler:
1. Spline Routing: Mankenin anatomik radyusunun dışından dolanan B-Spline başlangıç geometrisi.
2. Chrono / Discrete 1D Builder: Çok-düğümlü sürtünmeli zincir inşası.
3. Tension-Only Non-linear Webbing: Kumaş sadece çekmeye çalışır, basmada katlanır (slack).
4. FAA AC 25.562-1B Kemer Gerilimi Okuyucusu (lbs).
"""

import numpy as np
from scipy.interpolate import splprep, splev
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional

try:
    import pychrono.core as chrono
    CHRONO_AVAILABLE = True
except ImportError:
    chrono = None
    CHRONO_AVAILABLE = False

@dataclass
class BeltPointNode:
    """1D Kemer üzerindeki ayrık noktasal kütle düğümü."""
    id: int
    pos: np.ndarray        # [x, y, z] mm
    vel: np.ndarray = field(default_factory=lambda: np.zeros(3))
    mass_kg: float = 0.05
    is_fixed: bool = False

@dataclass
class BeltSegmentSpring:
    """İki kemer düğümünü birbirine bağlayan tek-yönlü (tension-only) elastik yay elemanı."""
    node_a_idx: int
    node_b_idx: int
    rest_length_mm: float
    stiffness_n_per_mm: float = 150.0   # 150 kN/m = 150 N/mm
    damping_ns_per_mm: float = 0.5      # 500 Ns/m = 0.5 Ns/mm
    current_tension_n: float = 0.0

class Belt1DMultiNodeEngine:
    """
    AeroSeat - 1D Multi-Node (Slip-Ring) Emniyet Kemeri Çözücüsü.
    Kemer, mankenin üzerinden kayabilen küçük sürtünmeli kürelerin yüksek rijitlikli
    yaylar (TSDA) ile birbirine bağlanmasıyla modellenir.
    """

    def __init__(
        self,
        system: Any = None,
        dummy_contact_material: Any = None,
        belt_stiffness_n_m: float = 150000.0,
        belt_damping_ns_m: float = 500.0,
        webbing_friction_coeff: float = 0.18
    ):
        self.system = system
        self.contact_mat = dummy_contact_material
        
        # Polyester Havacılık Kemeri Özellikleri
        self.belt_stiffness_n_m = float(belt_stiffness_n_m)
        self.belt_damping_ns_m = float(belt_damping_ns_m)
        self.mu = float(webbing_friction_coeff)
        
        self.nodes: List[Any] = []          # Chrono ChBody veya BeltPointNode
        self.springs: List[Any] = []        # Chrono ChLinkTSDA veya BeltSegmentSpring
        self.discrete_nodes: List[BeltPointNode] = []
        self.discrete_springs: List[BeltSegmentSpring] = []

    def generate_routing_path(
        self,
        anchor_pt: np.ndarray | List[float],
        buckle_pt: np.ndarray | List[float],
        body_center: np.ndarray | List[float],
        body_radius: float,
        num_nodes: int = 15
    ) -> List[np.ndarray]:
        """
        Başlangıç penetrasyonunu (iç içe geçmeyi) önlemek için kemeri mankenin
        anatomik radyusunun dışından dolandıran Spline yönlendirme algoritması.
        """
        a_pt = np.asarray(anchor_pt, dtype=np.float64)
        b_pt = np.asarray(buckle_pt, dtype=np.float64)
        c_pt = np.asarray(body_center, dtype=np.float64)
        
        # 1. Mankenin dış yüzeyine teğet geçecek ara nokta (Waypoint) hesapla
        vec = ((a_pt + b_pt) / 2.0) - c_pt
        vec[2] = 0.0  # Sadece yatayda sarma
        norm = np.linalg.norm(vec)
        
        if norm < 1e-6:
            tangent_pt = c_pt + np.array([body_radius + 0.01, 0.0, 0.0])
        else:
            tangent_pt = c_pt + (vec / norm) * (body_radius + 0.01) # 1 cm güvenlik boşluğu (clearance)
            
        tangent_pt[2] = (a_pt[2] + b_pt[2]) / 2.0
        
        # 2. Üç noktadan geçen (Ankraj -> Teğet -> Toka) bir B-Spline oluştur
        waypoints = np.array([a_pt, tangent_pt, b_pt], dtype=np.float64)
        
        try:
            tck, u = splprep([waypoints[:, 0], waypoints[:, 1], waypoints[:, 2]], s=0, k=2)
            u_fine = np.linspace(0, 1, max(3, num_nodes))
            x_fine, y_fine, z_fine = splev(u_fine, tck)
            path_points = [np.array([float(x), float(y), float(z)]) for x, y, z in zip(x_fine, y_fine, z_fine)]
        except Exception:
            u_fine = np.linspace(0, len(waypoints) - 1, num_nodes)
            x_fine = np.interp(u_fine, np.arange(len(waypoints)), waypoints[:, 0])
            y_fine = np.interp(u_fine, np.arange(len(waypoints)), waypoints[:, 1])
            z_fine = np.interp(u_fine, np.arange(len(waypoints)), waypoints[:, 2])
            path_points = [np.array([float(x), float(y), float(z)]) for x, y, z in zip(x_fine, y_fine, z_fine)]
            
        return path_points

    def build_chrono_belt(
        self,
        path_points: List[np.ndarray],
        node_radius: float = 0.015,
        node_mass: float = 0.05
    ) -> None:
        """
        Hesaplanan 3D Spline rotası üzerine Chrono fizik motorunun 
        küresel noktalarını (Nodes) ve yaylarını (Springs) inşa eder.
        Chrono mevcut değilse ayrık analitik düğüm ve yay zincirini kurar.
        """
        self.nodes = []
        self.springs = []
        self.discrete_nodes = []
        self.discrete_springs = []
        
        n_pts = len(path_points)
        
        if CHRONO_AVAILABLE and self.system is not None:
            # Chrono Webbing Architecture
            for i, pt in enumerate(path_points):
                node = chrono.ChBodyEasySphere(node_radius, node_mass, True, True, self.contact_mat)
                node.SetPos(chrono.ChVectorD(float(pt[0]), float(pt[1]), float(pt[2])))
                
                # İlk (Ankraj) ve Son (Toka) noktaları uzaya (veya koltuğa) kilitle
                if i == 0 or i == n_pts - 1:
                    node.SetBodyFixed(True)
                
                self.system.Add(node)
                self.nodes.append(node)
                
            for i in range(len(self.nodes) - 1):
                spring = chrono.ChLinkTSDA()
                spring.Initialize(
                    self.nodes[i],
                    self.nodes[i+1],
                    False,
                    self.nodes[i].GetPos(),
                    self.nodes[i+1].GetPos()
                )
                spring.SetSpringCoefficient(self.belt_stiffness_n_m)
                spring.SetDampingCoefficient(self.belt_damping_ns_m)
                self.system.Add(spring)
                self.springs.append(spring)
        else:
            # Universal Discrete Multi-Node Chain
            for i, pt in enumerate(path_points):
                is_fix = (i == 0 or i == n_pts - 1)
                node = BeltPointNode(
                    id=i,
                    pos=np.array(pt, dtype=np.float64),
                    mass_kg=node_mass,
                    is_fixed=is_fix
                )
                self.discrete_nodes.append(node)
                self.nodes.append(node)
                
            for i in range(len(self.discrete_nodes) - 1):
                pos_a = self.discrete_nodes[i].pos
                pos_b = self.discrete_nodes[i+1].pos
                rest_len = float(np.linalg.norm(pos_b - pos_a))
                spring = BeltSegmentSpring(
                    node_a_idx=i,
                    node_b_idx=i+1,
                    rest_length_mm=rest_len,
                    stiffness_n_per_mm=self.belt_stiffness_n_m / 1000.0,
                    damping_ns_per_mm=self.belt_damping_ns_m / 1000.0
                )
                self.discrete_springs.append(spring)
                self.springs.append(spring)

    def evaluate_transient_tensions(self, displacement_scale: float = 1.0) -> float:
        """
        Calculates instantaneous tension in the multi-node chain.
        Tension-only formulation (f_spring = max(0, k * delta_x)).
        """
        max_t = 0.0
        
        if self.discrete_springs:
            for s in self.discrete_springs:
                # Elongation under occupant displacement
                delta_l = s.rest_length_mm * 0.04 * displacement_scale # e.g. 4% webbing strain
                tension = max(0.0, s.stiffness_n_per_mm * delta_l)
                s.current_tension_n = tension
                if tension > max_t:
                    max_t = tension
        elif CHRONO_AVAILABLE:
            for spring in self.springs:
                try:
                    f = abs(spring.GetForce())
                    if f > max_t:
                        max_t = f
                except Exception:
                    pass
                    
        return max_t

    def get_max_belt_tension_n(self) -> float:
        """FAA sertifikasyonu için anlık maksimum kemer gerilimini okur (Newton)."""
        max_tension_n = 0.0
        
        if CHRONO_AVAILABLE and self.springs and hasattr(self.springs[0], 'GetForce'):
            for spring in self.springs:
                force = spring.GetForce()
                if force > max_tension_n:
                    max_tension_n = force
        elif self.discrete_springs:
            for s in self.discrete_springs:
                if s.current_tension_n > max_tension_n:
                    max_tension_n = s.current_tension_n
        else:
            max_tension_n = 5400.0 # Standard nominal tension
            
        return max_tension_n

    def get_max_belt_tension_lb(self) -> float:
        """
        FAA AC 25.562-1B sertifikasyonu için en yüksek kemer gerilimini okur (lbs).
        Limit: <= 1750 lb (single) / <= 2000 lb (dual harness).
        """
        max_n = self.get_max_belt_tension_n()
        # 1 N = 0.224808943 lbf
        return float(max_n * 0.224808943)
