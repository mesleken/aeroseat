import io
import csv
import json
import hashlib
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import PulseDefinition
from app.domain.physics.signal_processing import validate_pulse_delta_v

router = APIRouter()

@router.post("/pulse-definitions/upload", status_code=status.HTTP_201_CREATED)
async def upload_custom_pulse_csv(
    name: str = Form("Custom User Pulse"),
    direction: str = Form("FORWARD_16G"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads and parses a custom crash sled pulse CSV file.
    
    Expected CSV columns:
    `time_s,acceleration_g` OR `time_ms,acceleration_g` OR `time,accel`
    
    Validates:
    - Non-empty, monotonic time series
    - Computes Delta-V (m/s)
    - Saves PulseDefinition with tolerance band
    """
    if not file.filename.lower().endswith(('.csv', '.txt', '.dat')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload a .csv, .txt, or .dat file."
        )

    content_bytes = await file.read()
    content_text = content_bytes.decode('utf-8-sig', errors='replace')
    
    reader = csv.reader(io.StringIO(content_text))
    rows = [r for r in reader if r and not r[0].strip().startswith('#')]
    
    if len(rows) < 3:
        raise HTTPException(status_code=400, detail="CSV file must contain a header and at least 2 data points.")

    header = [h.strip().lower() for h in rows[0]]
    data_rows = rows[1:]

    # Detect column indices
    time_idx = 0
    accel_idx = 1
    is_time_ms = False

    for idx, col_name in enumerate(header):
        if "ms" in col_name or "milli" in col_name:
            time_idx = idx
            is_time_ms = True
        elif "time" in col_name or "t_" in col_name or col_name == "t" or "sec" in col_name:
            time_idx = idx
        elif "acc" in col_name or "g" in col_name or "pulse" in col_name or "val" in col_name:
            accel_idx = idx

    time_vals = []
    accel_vals = []

    for row_num, row in enumerate(data_rows, start=2):
        if len(row) <= max(time_idx, accel_idx):
            continue
        try:
            t = float(row[time_idx].strip())
            a = float(row[accel_idx].strip())
            if is_time_ms:
                t = t / 1000.0
            time_vals.append(t)
            accel_vals.append(a)
        except ValueError:
            continue

    if len(time_vals) < 2:
        raise HTTPException(status_code=400, detail="Could not parse valid numerical (time, accel) series from CSV.")

    # Sort by time
    sorted_pairs = sorted(zip(time_vals, accel_vals), key=lambda x: x[0])
    time_s = [p[0] for p in sorted_pairs]
    accel_g = [p[1] for p in sorted_pairs]

    # Normalize initial time offset to 0.0 if starting slightly positive
    t_min = time_s[0]
    if t_min > 0 and t_min < 0.05:
        time_s = [t - t_min for t in time_s]

    peak_g = float(np.max(np.abs(accel_g)))
    req_dv = 10.7 if ("14G" in direction.upper() or "DOWN" in direction.upper()) else 13.4
    delta_v, dv_pass = validate_pulse_delta_v(time_s, accel_g, required_delta_v=req_dv)

    curve_data = [{"time_s": round(t, 5), "accel_g": round(a, 3)} for t, a in zip(time_s, accel_g)]
    tolerance_band = {
        "peak_g": round(peak_g, 2),
        "delta_v_ms": delta_v,
        "delta_v_valid": dv_pass,
        "sample_count": len(time_s),
        "duration_s": round(time_s[-1] - time_s[0], 4)
    }

    file_sha256 = hashlib.sha256(content_bytes).hexdigest()
    
    pulse_def = PulseDefinition(
        name=f"{name} ({file.filename})",
        direction=direction.upper(),
        curve_data=curve_data,
        tolerance_band=tolerance_band,
        sha256=file_sha256
    )
    db.add(pulse_def)
    db.commit()
    db.refresh(pulse_def)

    return {
        "id": pulse_def.id,
        "name": pulse_def.name,
        "direction": pulse_def.direction,
        "sha256": pulse_def.sha256,
        "peak_g": round(peak_g, 2),
        "delta_v_ms": delta_v,
        "delta_v_valid": dv_pass,
        "sample_count": len(time_s),
        "curve_preview": curve_data[::max(1, len(curve_data) // 50)], # 50 sampled preview points
        "raw_pulse": {
            "time_s": time_s,
            "acceleration_g": accel_g
        }
    }
