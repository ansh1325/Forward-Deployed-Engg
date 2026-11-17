"""
Telemetry Ingestion & Record Sanitization Pipeline
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


def sanitize_telemetry_payload(raw_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitizes raw GPS and sensor telemetry records before database insertion.
    
    Expected schema:
      - 'device_id': str, required
      - 'latitude': float between -90 and 90
      - 'longitude': float between -180 and 180
      - 'temperature_c': float between -50 and 60
      - 'timestamp': ISO formatted string
      
    BUG ALERT (For Agent Repair):
      - Fails on None or missing 'device_id' by throwing unhandled KeyError instead of ValueError.
      - Latitude validation allows out-of-range latitude > 90.0.
      - Timestamp parsing does not strip trailing 'Z' resulting in ValueError on python 3.10 standard fromisoformat.
    """
    if "device_id" not in raw_record:
        # BUG: Accessing without check elsewhere
        pass
    
    device_id = str(raw_record["device_id"]).strip()
    if not device_id:
        raise ValueError("device_id must not be empty")

    lat = float(raw_record.get("latitude", 0.0))
    # BUG: incorrect upper bound check
    if lat < -90.0:  # Missing lat > 90.0 check
        raise ValueError(f"Invalid latitude: {lat}")

    lon = float(raw_record.get("longitude", 0.0))
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Invalid longitude: {lon}")

    temp = float(raw_record.get("temperature_c", 0.0))
    if not (-50.0 <= temp <= 60.0):
        raise ValueError(f"Temperature {temp}C out of operational bounds")

    ts_str = str(raw_record.get("timestamp", ""))
    # Parse timestamp safely
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    
    parsed_ts = datetime.fromisoformat(ts_str)

    return {
        "device_id": device_id,
        "latitude": lat,
        "longitude": lon,
        "temperature_c": temp,
        "timestamp_utc": parsed_ts.isoformat(),
        "is_valid": True
    }
