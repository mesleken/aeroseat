import numpy as np
from typing import Optional, Dict
from dataclasses import dataclass

from app.domain.physics.lumped_mass_model import BeltAnchorGeometry

@dataclass
class CadAnchorInput:
    """Represents candidate anchor coordinates picked from 3D CAD viewer or STEP model."""
    d_ring_xyz: tuple[float, float, float]
    buckle_xyz: tuple[float, float, float]
    lap_anchor_left_xyz: tuple[float, float, float]
    lap_anchor_right_xyz: tuple[float, float, float]

class GeometryExtractionEngine:
    """
    Extracts, validates, and transforms CAD / STEP 3D anchor coordinates into physical BeltAnchorGeometry.
    Supports semi-automated user picking from ThreeSeatViewer.jsx or automated centroid mapping.
    """

    @staticmethod
    def create_belt_geometry_from_cad(cad_input: CadAnchorInput) -> BeltAnchorGeometry:
        """Constructs BeltAnchorGeometry from verified 3D CAD coordinates (in meters)."""
        return BeltAnchorGeometry(
            d_ring_xyz=tuple(float(x) for x in cad_input.d_ring_xyz),
            buckle_xyz=tuple(float(x) for x in cad_input.buckle_xyz),
            lap_anchor_l=tuple(float(x) for x in cad_input.lap_anchor_left_xyz),
            lap_anchor_r=tuple(float(x) for x in cad_input.lap_anchor_right_xyz)
        )

    @staticmethod
    def estimate_anchors_from_seat_bounds(
        seat_bbox_min_m: tuple[float, float, float],
        seat_bbox_max_m: tuple[float, float, float]
    ) -> BeltAnchorGeometry:
        """
        Heuristically calculates nominal aviation restraint anchors from seat frame bounding box.
        """
        b_min = np.array(seat_bbox_min_m, dtype=np.float64)
        b_max = np.array(seat_bbox_max_m, dtype=np.float64)
        
        # Upper shoulder guide: near upper-rear of backrest
        d_ring = (
            float(b_min[0] + 0.20 * (b_max[0] - b_min[0])),
            float(b_min[1] + 0.85 * (b_max[1] - b_min[1])),
            float(b_min[2] + 0.90 * (b_max[2] - b_min[2]))
        )
        
        # Central stalk buckle: near seat pan midpoint
        buckle = (
            float(b_min[0] + 0.45 * (b_max[0] - b_min[0])),
            float(b_min[1] + 0.70 * (b_max[1] - b_min[1])),
            float(b_min[2] + 0.40 * (b_max[2] - b_min[2]))
        )
        
        # Lap anchors
        lap_l = (
            float(b_min[0] + 0.40 * (b_max[0] - b_min[0])),
            float(b_min[1] + 0.15 * (b_max[1] - b_min[1])),
            float(b_min[2] + 0.35 * (b_max[2] - b_min[2]))
        )
        lap_r = (
            float(b_min[0] + 0.40 * (b_max[0] - b_min[0])),
            float(b_min[1] + 0.85 * (b_max[1] - b_min[1])),
            float(b_min[2] + 0.35 * (b_max[2] - b_min[2]))
        )

        return BeltAnchorGeometry(
            d_ring_xyz=d_ring,
            buckle_xyz=buckle,
            lap_anchor_l=lap_l,
            lap_anchor_r=lap_r
        )
