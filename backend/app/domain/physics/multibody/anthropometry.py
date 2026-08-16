class AnthropometricDataset:
    """Biomechanical Anthropometric Parameter Dataset (SAE / FAA Hybrid III).
    
    Presets:
    - FAA_HIII_5F: 5th Percentile Female (Mass: 49.0 kg, Stature: 1.50 m)
    - FAA_HIII_50M: 50th Percentile Male (Mass: 77.7 kg, Stature: 1.75 m)
    - FAA_HIII_95M: 95th Percentile Male (Mass: 102.0 kg, Stature: 1.88 m)
    """
    
    PRESETS = {
        "FAA_HIII_5F": {
            "total_mass_kg": 49.0,
            "stature_m": 1.50,
            "head_mass_kg": 3.72,
            "torso_mass_kg": 21.5,
            "pelvis_mass_kg": 10.2,
            "femur_mass_kg": 5.8,
            "head_inertia_yy": 0.017,
            "torso_inertia_yy": 1.45,
            "neck_length_m": 0.115,
            "lumbar_height_m": 0.210
        },
        "FAA_HIII_50M": {
            "total_mass_kg": 77.7,
            "stature_m": 1.75,
            "head_mass_kg": 4.54,
            "torso_mass_kg": 34.2,
            "pelvis_mass_kg": 14.8,
            "femur_mass_kg": 8.6,
            "head_inertia_yy": 0.024,
            "torso_inertia_yy": 2.25,
            "neck_length_m": 0.135,
            "lumbar_height_m": 0.250
        },
        "FAA_HIII_95M": {
            "total_mass_kg": 102.0,
            "stature_m": 1.88,
            "head_mass_kg": 5.12,
            "torso_mass_kg": 45.8,
            "pelvis_mass_kg": 19.5,
            "femur_mass_kg": 11.2,
            "head_inertia_yy": 0.031,
            "torso_inertia_yy": 3.10,
            "neck_length_m": 0.150,
            "lumbar_height_m": 0.280
        }
    }

    @classmethod
    def get_preset(cls, dummy_type: str = "FAA_HIII_50M") -> dict:
        """Returns anthropometric parameter dict for target dummy preset."""
        return cls.PRESETS.get(dummy_type, cls.PRESETS["FAA_HIII_50M"])
