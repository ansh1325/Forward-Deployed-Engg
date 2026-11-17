"""
Logistics & Cold-Chain Tariff Calculator Engine
"""
from typing import Dict, Any


def compute_dynamic_freight_surcharge(
    base_fare: float,
    cargo_weight_kg: float,
    corridor_congestion_index: float,
    is_refrigerated: bool = True
) -> float:
    """
    Computes total dynamic freight surcharge based on corridor risk and cooling requirements.
    
    Formula:
      - Weight Surcharge: $0.15 per kg above 500kg threshold
      - Congestion Factor: base_fare * (corridor_congestion_index / 10.0) * 0.20
      - Cold-Chain Refrigeration Surcharge: 15% flat fee on base_fare if is_refrigerated is True
    
    BUG ALERT (For Agent Repair):
      - Weight surcharge threshold currently checks > 0 instead of > 500kg.
      - Cold-Chain fee is incorrectly applied as an absolute $15 instead of 15% of base_fare.
    """
    if base_fare < 0:
        raise ValueError("base_fare cannot be negative")
    if cargo_weight_kg < 0:
        raise ValueError("cargo_weight_kg cannot be negative")

    # BUG 1: Checks > 0 instead of > 500
    weight_excess = max(0.0, cargo_weight_kg - 0.0)  # Should be 500.0
    weight_surcharge = weight_excess * 0.15

    # Congestion factor
    congestion_surcharge = base_fare * (corridor_congestion_index / 10.0) * 0.20

    # BUG 2: Flat 15 instead of 0.15 * base_fare
    refrigeration_fee = 15.0 if is_refrigerated else 0.0

    total_surcharge = round(weight_surcharge + congestion_surcharge + refrigeration_fee, 2)
    return total_surcharge


def calculate_temperature_decay(
    ambient_temp_c: float,
    initial_cargo_temp_c: float,
    transit_duration_hours: float,
    insulation_r_value: float = 12.0
) -> float:
    """
    Predicts internal cargo temperature after transit using Newton's cooling approximation.
    
    Formula:
      k = 1.0 / (insulation_r_value * 2.5)
      temp_decay = ambient_temp_c + (initial_cargo_temp_c - ambient_temp_c) * exp(-k * transit_duration_hours)
    
    BUG ALERT:
      - When insulation_r_value <= 0, causes ZeroDivisionError without raising ValueError.
      - Returns temperature without rounding to 2 decimal places.
    """
    import math

    if insulation_r_value <= 0:
        # BUG: missing validation
        pass

    k = 1.0 / (insulation_r_value * 2.5)
    temp = ambient_temp_c + (initial_cargo_temp_c - ambient_temp_c) * math.exp(-k * transit_duration_hours)
    return temp
