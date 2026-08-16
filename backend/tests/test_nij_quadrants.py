import pytest
import numpy as np
from app.domain.injury_metrics import calculate_nij

def test_nij_tension_flexion():
    """Quadrant 1: +Fz (Tension), +My (Flexion)"""
    fz = np.array([6811.0]) # Fzc = 6811 N -> 1.0
    my = np.array([310.0])  # Myc = 310 Nm -> 1.0
    nij_val, mode = calculate_nij(fz, my)
    
    assert nij_val == 2.0
    assert mode == "Tension-Flexion"

def test_nij_tension_extension():
    """Quadrant 2: +Fz (Tension), -My (Extension)"""
    fz = np.array([6811.0])  # Fzc = 6811 N -> 1.0
    my = np.array([-135.0])  # Myc_ext = 135 Nm -> 1.0
    nij_val, mode = calculate_nij(fz, my)
    
    assert nij_val == 2.0
    assert mode == "Tension-Extension"

def test_nij_compression_flexion():
    """Quadrant 3: -Fz (Compression), +My (Flexion)"""
    fz = np.array([-6160.0]) # Fzc_comp = 6160 N -> 1.0
    my = np.array([310.0])   # Myc = 310 Nm -> 1.0
    nij_val, mode = calculate_nij(fz, my)
    
    assert nij_val == 2.0
    assert mode == "Compression-Flexion"

def test_nij_compression_extension():
    """Quadrant 4: -Fz (Compression), -My (Extension)"""
    fz = np.array([-6160.0]) # Fzc_comp = 6160 N -> 1.0
    my = np.array([-135.0])  # Myc_ext = 135 Nm -> 1.0
    nij_val, mode = calculate_nij(fz, my)
    
    assert nij_val == 2.0
    assert mode == "Compression-Extension"
