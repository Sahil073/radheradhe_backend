"""
Test cases for optimization algorithms
"""

import pytest
from services.optimization_service import energy_optimizer

def test_emergency_mode():
    """Test emergency mode optimization"""
    sensor_data = {
        "Zone1": {"batteryPercentage": 5, "inputPower": 10, "outputPower": 15},
        "Zone2": {"batteryPercentage": 5, "inputPower": 8, "outputPower": 12},
        "Zone3": {"batteryPercentage": 5, "inputPower": 5, "outputPower": 8},
        "Zone4": {"batteryPercentage": 5, "inputPower": 3, "outputPower": 6}
    }
    
    decisions = energy_optimizer._emergency_mode(sensor_data)
    
    # Only critical zones should be ON
    assert decisions["Zone1"] == "ON"  # Critical
    assert decisions["Zone2"] == "OFF"  # Semi-critical
    assert decisions["Zone3"] == "OFF"  # Non-critical
    assert decisions["Zone4"] == "OFF"  # Deferrable

def test_efficiency_calculation():
    """Test efficiency calculation"""
    zone_data = {
        "inputPower": 50,
        "outputPower": 40,
        "batteryVoltage": 12.6
    }
    
    efficiency = energy_optimizer._calculate_efficiency(zone_data)
    
    assert 0 <= efficiency <= 1
    assert efficiency > 0.5  # Should be reasonably efficient

def test_load_balancing():
    """Test load balancing algorithm"""
    decisions = {
        "Zone1": "ON",
        "Zone2": "ON", 
        "Zone3": "ON",
        "Zone4": "ON"
    }
    
    sensor_data = {
        "Zone1": {"inputPower": 20, "outputPower": 25},
        "Zone2": {"inputPower": 15, "outputPower": 20},
        "Zone3": {"inputPower": 10, "outputPower": 15},
        "Zone4": {"inputPower": 5, "outputPower": 10}
    }
    
    balanced_decisions = energy_optimizer._apply_load_balancing(decisions, sensor_data)
    
    # Should maintain critical zones
    assert balanced_decisions["Zone1"] == "ON"
    
    # May turn off lower priority zones if overloaded
    total_output = sum(data["outputPower"] for data in sensor_data.values())
    total_input = sum(data["inputPower"] for data in sensor_data.values())
    
    if total_output > total_input * 0.9:
        # Some non-critical zones should be turned off
        off_zones = [zone for zone, decision in balanced_decisions.items() if decision == "OFF"]
        assert len(off_zones) > 0

def test_optimization_schedule():
    """Test optimization schedule generation"""
    schedule = energy_optimizer.get_optimization_schedule(6)
    
    assert len(schedule) == 6
    assert all('time' in entry for entry in schedule)
    assert all('predicted_demand' in entry for entry in schedule)
    assert all('recommended_action' in entry for entry in schedule)