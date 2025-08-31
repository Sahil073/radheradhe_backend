"""
Enhanced Scenario Controller with advanced optimization algorithms
"""

from services.firebase_service import set_command
from services.optimization_service import energy_optimizer
from config import Config
import logging

logger = logging.getLogger(__name__)

def apply_scenarios(sensor_data):
    """
    Apply enhanced optimization scenarios
    This is the legacy function - new code should use energy_optimizer directly
    """
    try:
        result = energy_optimizer.optimize_energy_allocation(sensor_data)
        
        if result["success"]:
            logger.info("Scenarios applied successfully via optimization service")
            return result
        else:
            logger.error(f"Scenario application failed: {result.get('error')}")
            return result
            
    except Exception as e:
        logger.error(f"Scenario application error: {e}")
        return {"success": False, "error": str(e)}

def apply_emergency_scenario(sensor_data, emergency_type):
    """
    Apply emergency scenarios based on emergency type
    """
    try:
        decisions = {}
        
        if emergency_type == "BATTERY_CRITICAL":
            # Only critical zones ON
            for zone, config in Config.ZONES.items():
                if config["type"] == "critical":
                    decisions[zone] = "ON"
                else:
                    decisions[zone] = "OFF"
                    
        elif emergency_type == "OVERLOAD":
            # Shed non-essential loads
            for zone, config in Config.ZONES.items():
                if config["type"] in ["critical", "semi-critical"]:
                    decisions[zone] = "ON"
                else:
                    decisions[zone] = "OFF"
                    
        elif emergency_type == "GRID_FAILURE":
            # Optimize for maximum battery life
            for zone, config in Config.ZONES.items():
                zone_data = sensor_data.get(zone, {})
                efficiency = energy_optimizer._calculate_efficiency(zone_data)
                
                if config["type"] == "critical":
                    decisions[zone] = "ON"
                elif config["type"] == "semi-critical" and efficiency > 0.8:
                    decisions[zone] = "ON"
                else:
                    decisions[zone] = "OFF"
        
        # Execute emergency decisions
        execution_results = {}
        for zone, command in decisions.items():
            success = set_command(zone, command)
            execution_results[zone] = success
        
        logger.info(f"Emergency scenario applied: {emergency_type}")
        
        return {
            "success": True,
            "emergency_type": emergency_type,
            "decisions": decisions,
            "execution_results": execution_results
        }
        
    except Exception as e:
        logger.error(f"Emergency scenario error: {e}")
        return {"success": False, "error": str(e)}

def apply_time_based_scenario(sensor_data, time_of_day):
    """
    Apply time-based optimization scenarios
    """
    try:
        decisions = {}
        
        # Morning scenario (6-10 AM)
        if 6 <= time_of_day <= 10:
            for zone, config in Config.ZONES.items():
                if config["type"] in ["critical", "semi-critical"]:
                    decisions[zone] = "ON"
                elif config["type"] == "deferrable":  # Water pumps, etc.
                    decisions[zone] = "ON"  # Good time for water pumping
                else:
                    decisions[zone] = "OFF"
        
        # Daytime scenario (10 AM - 6 PM)
        elif 10 <= time_of_day <= 18:
            # Solar generation peak - can run more loads
            for zone, config in Config.ZONES.items():
                zone_data = sensor_data.get(zone, {})
                solar_gen = zone_data.get("solarGeneration", 0)
                
                if config["type"] == "critical":
                    decisions[zone] = "ON"
                elif solar_gen > 20:  # Good solar generation
                    decisions[zone] = "ON"
                else:
                    decisions[zone] = "OFF"
        
        # Evening scenario (6 PM - 10 PM)
        elif 18 <= time_of_day <= 22:
            for zone, config in Config.ZONES.items():
                if config["type"] in ["critical", "semi-critical"]:
                    decisions[zone] = "ON"  # Street lights, etc.
                elif config["type"] == "non-critical":
                    decisions[zone] = "ON"  # Entertainment time
                else:
                    decisions[zone] = "OFF"
        
        # Night scenario (10 PM - 6 AM)
        else:
            for zone, config in Config.ZONES.items():
                if config["type"] == "critical":
                    decisions[zone] = "ON"
                elif config["type"] == "semi-critical":
                    decisions[zone] = "ON"  # Street lights for safety
                else:
                    decisions[zone] = "OFF"  # Save energy at night
        
        # Execute decisions
        execution_results = {}
        for zone, command in decisions.items():
            success = set_command(zone, command)
            execution_results[zone] = success
        
        logger.info(f"Time-based scenario applied for hour {time_of_day}")
        
        return {
            "success": True,
            "scenario_type": "TIME_BASED",
            "time_of_day": time_of_day,
            "decisions": decisions,
            "execution_results": execution_results
        }
        
    except Exception as e:
        logger.error(f"Time-based scenario error: {e}")
        return {"success": False, "error": str(e)}

def apply_weather_based_scenario(sensor_data, weather_forecast):
    """
    Apply weather-based optimization scenarios
    """
    try:
        decisions = {}
        
        # Cloudy/rainy weather - conserve energy
        if weather_forecast.get("condition") in ["cloudy", "rainy"]:
            for zone, config in Config.ZONES.items():
                zone_data = sensor_data.get(zone, {})
                battery_level = zone_data.get("batteryPercentage", 50)
                
                if config["type"] == "critical":
                    decisions[zone] = "ON"
                elif config["type"] == "semi-critical" and battery_level > 30:
                    decisions[zone] = "ON"
                else:
                    decisions[zone] = "OFF"
        
        # Sunny weather - can run more loads
        elif weather_forecast.get("condition") == "sunny":
            for zone, config in Config.ZONES.items():
                if config["type"] in ["critical", "semi-critical", "non-critical"]:
                    decisions[zone] = "ON"
                else:
                    # Deferrable loads - check solar generation
                    zone_data = sensor_data.get(zone, {})
                    solar_gen = zone_data.get("solarGeneration", 0)
                    decisions[zone] = "ON" if solar_gen > 30 else "OFF"
        
        # Execute decisions
        execution_results = {}
        for zone, command in decisions.items():
            success = set_command(zone, command)
            execution_results[zone] = success
        
        logger.info(f"Weather-based scenario applied: {weather_forecast.get('condition')}")
        
        return {
            "success": True,
            "scenario_type": "WEATHER_BASED",
            "weather": weather_forecast,
            "decisions": decisions,
            "execution_results": execution_results
        }
        
    except Exception as e:
        logger.error(f"Weather-based scenario error: {e}")
        return {"success": False, "error": str(e)}