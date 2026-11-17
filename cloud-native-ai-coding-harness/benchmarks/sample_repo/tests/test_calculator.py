import pytest
from app.calculator import compute_dynamic_freight_surcharge, calculate_temperature_decay


def test_freight_surcharge_under_threshold():
    # Weight 300kg is under the 500kg threshold -> weight surcharge should be $0
    # base_fare = 1000.0, congestion = 5.0 -> congestion surcharge = 1000 * 0.5 * 0.2 = $100.0
    # is_refrigerated = True -> 15% of 1000.0 = $150.0
    # Total expected: 0 + 100.0 + 150.0 = 250.0
    surcharge = compute_dynamic_freight_surcharge(
        base_fare=1000.0,
        cargo_weight_kg=300.0,
        corridor_congestion_index=5.0,
        is_refrigerated=True
    )
    assert surcharge == 250.0, f"Expected 250.0 but got {surcharge}"


def test_freight_surcharge_above_threshold():
    # Weight 700kg -> excess = 200kg * 0.15 = $30.0
    # base_fare = 500.0, congestion = 0.0 -> $0
    # is_refrigerated = False -> $0
    # Total expected = 30.0
    surcharge = compute_dynamic_freight_surcharge(
        base_fare=500.0,
        cargo_weight_kg=700.0,
        corridor_congestion_index=0.0,
        is_refrigerated=False
    )
    assert surcharge == 30.0, f"Expected 30.0 but got {surcharge}"


def test_temperature_decay_normal():
    # Ambient 30C, Initial 4C, Duration 10h, R-value 12
    temp = calculate_temperature_decay(
        ambient_temp_c=30.0,
        initial_cargo_temp_c=4.0,
        transit_duration_hours=10.0,
        insulation_r_value=12.0
    )
    assert round(temp, 2) == 11.37


def test_temperature_decay_invalid_insulation():
    with pytest.raises(ValueError):
        calculate_temperature_decay(
            ambient_temp_c=30.0,
            initial_cargo_temp_c=4.0,
            transit_duration_hours=10.0,
            insulation_r_value=0.0
        )
