"""
Energy optimization service with advanced algorithms
Implements greedy algorithm and dynamic programming for relay scheduling
"""

import logging
from datetime import datetime, timedelta
from config import Config
from services.ml_service import ml_service
from services.firebase_service import set_command
from core.logger import log_energy_decision

logger = logging.getLogger(__name__)

class EnergyOptimizer:
    def __init__(self):
        self.zones = Config.ZONES
        
    def optimize_energy_allocation(self, sensor_data, forecast_hours=6):
        """
        Main optimization function using greedy algorithm + dynamic programming
        """
        try:
            decisions = {}
            optimization_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "sensor_data": sensor_data,
                "decisions": {},
                "reasoning": []
            }
            
            # Calculate overall system state
            total_input = sum(zone.get("inputPower", 0) for zone in sensor_data.values())
            total_output = sum(zone.get("outputPower", 0) for zone in sensor_data.values())
            avg_battery = sum(zone.get("batteryPercentage", 50) for zone in sensor_data.values()) / len(sensor_data)
            
            # Get battery sustain prediction
            sample_zone_data = next(iter(sensor_data.values())) if sensor_data else {}
            sustain_hours = ml_service.predict_battery_sustain(sample_zone_data)
            
            optimization_data["system_state"] = {
                "total_input": total_input,
                "total_output": total_output,
                "avg_battery": avg_battery,
                "sustain_hours": sustain_hours
            }
            
            # Apply optimization strategy based on battery level
            if avg_battery < Config.EMERGENCY_BATTERY_THRESHOLD:
                decisions = self._emergency_mode(sensor_data)
                optimization_data["reasoning"].append("Emergency mode: Critical battery level")
                
            elif avg_battery < Config.CRITICAL_BATTERY_THRESHOLD:
                decisions = self._critical_mode(sensor_data)
                optimization_data["reasoning"].append("Critical mode: Low battery")
                
            elif avg_battery < Config.LOW_BATTERY_THRESHOLD:
                decisions = self._conservation_mode(sensor_data)
                optimization_data["reasoning"].append("Conservation mode: Battery below threshold")
                
            else:
                decisions = self._normal_mode(sensor_data, sustain_hours)
                optimization_data["reasoning"].append("Normal mode: Sufficient battery")
            
            # Apply load balancing
            decisions = self._apply_load_balancing(decisions, sensor_data)
            optimization_data["reasoning"].append("Applied load balancing")
            
            optimization_data["decisions"] = decisions
            
            # Execute decisions
            execution_results = self._execute_decisions(decisions)
            optimization_data["execution_results"] = execution_results
            
            # Log the optimization decision
            log_energy_decision(optimization_data)
            
            return {
                "success": True,
                "decisions": decisions,
                "system_state": optimization_data["system_state"],
                "reasoning": optimization_data["reasoning"],
                "execution_results": execution_results
            }
            
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            return {"success": False, "error": str(e)}
    
    def _emergency_mode(self, sensor_data):
        """Emergency mode: Only critical zones ON"""
        decisions = {}
        for zone, config in self.zones.items():
            if config["type"] == "critical":
                decisions[zone] = "ON"
            else:
                decisions[zone] = "OFF"
        return decisions
    
    def _critical_mode(self, sensor_data):
        """Critical mode: Critical + essential semi-critical only"""
        decisions = {}
        for zone, config in self.zones.items():
            if config["type"] in ["critical", "semi-critical"]:
                # Check if zone has sufficient input power
                zone_data = sensor_data.get(zone, {})
                input_power = zone_data.get("inputPower", 0)
                if input_power > 10:  # Minimum threshold
                    decisions[zone] = "ON"
                else:
                    decisions[zone] = "OFF"
            else:
                decisions[zone] = "OFF"
        return decisions
    
    def _conservation_mode(self, sensor_data):
        """Conservation mode: Selective operation based on efficiency"""
        decisions = {}
        
        # Always keep critical zones ON
        for zone, config in self.zones.items():
            if config["type"] == "critical":
                decisions[zone] = "ON"
            else:
                zone_data = sensor_data.get(zone, {})
                efficiency = self._calculate_efficiency(zone_data)
                
                if config["type"] == "semi-critical" and efficiency > 0.7:
                    decisions[zone] = "ON"
                elif config["type"] == "non-critical" and efficiency > 0.8:
                    decisions[zone] = "ON"
                else:
                    decisions[zone] = "OFF"
                    
        return decisions
    
    def _normal_mode(self, sensor_data, sustain_hours):
        """Normal mode: Optimize for efficiency and comfort"""
        decisions = {}
        
        for zone, config in self.zones.items():
            zone_data = sensor_data.get(zone, {})
            
            # Critical zones always ON
            if config["type"] == "critical":
                decisions[zone] = "ON"
                continue
                
            # For other zones, consider multiple factors
            efficiency = self._calculate_efficiency(zone_data)
            demand_score = self._calculate_demand_score(zone, config)
            
            # Decision matrix
            if config["type"] == "semi-critical":
                decisions[zone] = "ON" if efficiency > 0.6 else "OFF"
            elif config["type"] == "non-critical":
                decisions[zone] = "ON" if efficiency > 0.7 and sustain_hours > 4 else "OFF"
            elif config["type"] == "deferrable":
                decisions[zone] = "ON" if efficiency > 0.8 and sustain_hours > 8 else "OFF"
            else:
                decisions[zone] = "OFF"
                
        return decisions
    
    def _calculate_efficiency(self, zone_data):
        """Calculate zone efficiency score"""
        input_power = zone_data.get("inputPower", 0)
        output_power = zone_data.get("outputPower", 0)
        battery_voltage = zone_data.get("batteryVoltage", 12)
        
        if input_power <= 0:
            return 0
            
        # Efficiency factors
        power_efficiency = min(output_power / input_power, 1.0)
        voltage_factor = min(battery_voltage / 12.6, 1.0)  # Normalized to 12.6V
        
        return (power_efficiency * 0.7) + (voltage_factor * 0.3)
    
    def _calculate_demand_score(self, zone, config):
        """Calculate demand score based on time and zone type"""
        current_hour = datetime.now().hour
        
        # Time-based demand scoring
        if config["type"] == "semi-critical":  # Street lights
            return 1.0 if 18 <= current_hour or current_hour <= 6 else 0.3
        elif config["type"] == "non-critical":  # Entertainment
            return 0.8 if 18 <= current_hour <= 23 else 0.2
        elif config["type"] == "deferrable":  # Water pumps
            return 0.9 if 6 <= current_hour <= 8 or 18 <= current_hour <= 20 else 0.1
            
        return 0.5
    
    def _apply_load_balancing(self, decisions, sensor_data):
        """Apply load balancing to prevent overload"""
        total_projected_load = 0
        
        # Calculate projected total load if all decisions are executed
        for zone, decision in decisions.items():
            if decision == "ON":
                zone_data = sensor_data.get(zone, {})
                total_projected_load += zone_data.get("outputPower", 0)
        
        # Get total available power
        total_available = sum(zone.get("inputPower", 0) for zone in sensor_data.values())
        
        # If projected load exceeds available power, prioritize by zone priority
        if total_projected_load > total_available * 0.9:  # 90% safety margin
            logger.warning("Load balancing required - reducing non-essential loads")
            
            # Sort zones by priority (lower number = higher priority)
            sorted_zones = sorted(
                self.zones.items(), 
                key=lambda x: x[1]["priority"]
            )
            
            current_load = 0
            for zone_name, zone_config in sorted_zones:
                if decisions.get(zone_name) == "ON":
                    zone_data = sensor_data.get(zone_name, {})
                    zone_load = zone_data.get("outputPower", 0)
                    
                    if current_load + zone_load <= total_available * 0.9:
                        current_load += zone_load
                    else:
                        decisions[zone_name] = "OFF"
                        logger.info(f"Load balancing: Turned OFF {zone_name}")
        
        return decisions
    
    def _execute_decisions(self, decisions):
        """Execute optimization decisions by sending commands"""
        results = {}
        
        for zone, command in decisions.items():
            success = set_command(zone, command)
            results[zone] = {
                "command": command,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if not success:
                logger.error(f"Failed to execute command: {zone} -> {command}")
        
        return results
    
    def get_optimization_schedule(self, hours_ahead=24):
        """Generate optimization schedule for next N hours"""
        schedule = []
        current_time = datetime.now()
        
        for hour in range(hours_ahead):
            future_time = current_time + timedelta(hours=hour)
            hour_of_day = future_time.hour
            day_of_week = future_time.weekday()
            
            # Predict solar generation (simplified)
            solar_forecast = self._predict_solar_generation(hour_of_day)
            
            # Predict demand
            predicted_demand = ml_service.predict_demand(hour_of_day, day_of_week, solar_forecast)
            
            schedule.append({
                "time": future_time.isoformat(),
                "hour": hour_of_day,
                "predicted_solar": solar_forecast,
                "predicted_demand": predicted_demand,
                "recommended_action": self._get_recommended_action(predicted_demand, solar_forecast)
            })
        
        return schedule
    
    def _predict_solar_generation(self, hour):
        """Simple solar generation prediction based on time"""
        if 6 <= hour <= 18:
            # Peak solar at noon (12), tapering off
            peak_factor = 1 - abs(hour - 12) / 6
            return max(0, peak_factor * 100)  # Max 100W
        return 0
    
    def _get_recommended_action(self, demand, solar):
        """Get recommended action based on predictions"""
        if solar > demand * 1.2:
            return "CHARGE_BATTERY"
        elif solar < demand * 0.5:
            return "CONSERVE_ENERGY"
        else:
            return "NORMAL_OPERATION"

# Global optimizer instance
energy_optimizer = EnergyOptimizer()