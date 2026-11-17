import pytest
from app.data_pipeline import sanitize_telemetry_payload


def test_sanitize_valid_payload():
    payload = {
        "device_id": "SENSOR-TRUCK-99",
        "latitude": 34.0522,
        "longitude": -118.2437,
        "temperature_c": 3.8,
        "timestamp": "2026-11-17T12:00:00Z"
    }
    result = sanitize_telemetry_payload(payload)
    assert result["is_valid"] is True
    assert result["device_id"] == "SENSOR-TRUCK-99"
    assert result["temperature_c"] == 3.8


def test_sanitize_missing_device_id():
    payload = {
        "latitude": 34.0522,
        "longitude": -118.2437,
        "temperature_c": 3.8,
        "timestamp": "2026-11-17T12:00:00Z"
    }
    with pytest.raises(ValueError):
        sanitize_telemetry_payload(payload)


def test_sanitize_invalid_latitude():
    payload = {
        "device_id": "SENSOR-1",
        "latitude": 95.0,  # Invalid latitude > 90
        "longitude": 10.0,
        "temperature_c": 4.0,
        "timestamp": "2026-11-17T12:00:00Z"
    }
    with pytest.raises(ValueError):
        sanitize_telemetry_payload(payload)
