"""
Enhanced Energy Controller with comprehensive energy management
"""

from flask import request, jsonify
from services.firebase_service import get_sensor_data, get_zone_status
from services.ml_service import ml_service
from services.database_service import get_energy_history, store_energy_data
from services.optimization_service import energy_optimizer
from config import Config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def energy_status():
    """Get comprehensive energy status"""
    try:
        # Get real-time data
        sensor_data = get_sensor_data()
        if not sensor_data:
            return jsonify({"message": "No sensor data available"}), 404
        
        # Calculate system-wide metrics
        system_metrics = calculate_system_metrics(sensor_data)
        
        # Get predictions and anomalies for each zone
        zone_analysis = {}
        for zone, data in sensor_data.items():
            sustain_hours = ml_service.predict_battery_sustain(data)
            anomaly_result = ml_service.detect_anomaly(data)
            
            zone_analysis[zone] = {
                "current_data": data,
                "sustain_hours": sustain_hours,
                "anomaly": anomaly_result,
                "zone_config": Config.ZONES.get(zone, {}),
                "efficiency": energy_optimizer._calculate_efficiency(data)
            }
        
        return jsonify({
            "timestamp": datetime.utcnow().isoformat(),
            "system_metrics": system_metrics,
            "zones": zone_analysis,
            "optimization_recommendations": get_optimization_recommendations(sensor_data)
        })
        
    except Exception as e:
        logger.error(f"Energy status error: {e}")
        return jsonify({"message": "Failed to get energy status"}), 500

def update_voltage():
    """Receive voltage updates from ESP32 devices"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided"}), 400
        
        zone = data.get("zone")
        voltage = data.get("voltage")
        
        if not zone or voltage is None:
            return jsonify({"message": "Zone and voltage required"}), 400
        
        if zone not in Config.ZONES:
            return jsonify({"message": "Invalid zone"}), 400
        
        # Store the voltage update
        energy_data = {
            "batteryVoltage": voltage,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "esp32_update"
        }
        
        success = store_energy_data(zone, energy_data)
        
        if success:
            logger.info(f"Voltage updated for {zone}: {voltage}V")
            return jsonify({"message": "Voltage updated successfully"})
        else:
            return jsonify({"message": "Failed to store voltage data"}), 500
            
    except Exception as e:
        logger.error(f"Voltage update error: {e}")
        return jsonify({"message": "Internal server error"}), 500

def get_zone_history():
    """Get historical data for specific zone"""
    try:
        zone = request.args.get("zone")
        hours = int(request.args.get("hours", 24))
        
        if not zone:
            return jsonify({"message": "Zone parameter required"}), 400
            
        if zone not in Config.ZONES:
            return jsonify({"message": "Invalid zone"}), 400
        
        history = get_energy_history(zone, hours)
        
        return jsonify({
            "zone": zone,
            "hours": hours,
            "data_points": len(history),
            "history": history
        })
        
    except Exception as e:
        logger.error(f"Zone history error: {e}")
        return jsonify({"message": "Failed to get zone history"}), 500

def run_optimization():
    """Manually trigger optimization"""
    try:
        sensor_data = get_sensor_data()
        if not sensor_data:
            return jsonify({"message": "No sensor data available"}), 404
        
        result = energy_optimizer.optimize_energy_allocation(sensor_data)
        
        return jsonify({
            "message": "Optimization completed",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Manual optimization error: {e}")
        return jsonify({"message": "Optimization failed"}), 500

def get_predictions():
    """Get ML predictions for energy planning"""
    try:
        sensor_data = get_sensor_data()
        if not sensor_data:
            return jsonify({"message": "No sensor data available"}), 404
        
        predictions = {}
        
        for zone, data in sensor_data.items():
            # Battery sustain prediction
            sustain_hours = ml_service.predict_battery_sustain(data)
            
            # Demand prediction for next few hours
            current_hour = datetime.now().hour
            demand_predictions = []
            
            for hour_offset in range(1, 7):  # Next 6 hours
                future_hour = (current_hour + hour_offset) % 24
                predicted_demand = ml_service.predict_demand(
                    future_hour, 
                    datetime.now().weekday(),
                    energy_optimizer._predict_solar_generation(future_hour)
                )
                demand_predictions.append({
                    "hour": future_hour,
                    "predicted_demand": predicted_demand
                })
            
            predictions[zone] = {
                "sustain_hours": sustain_hours,
                "demand_forecast": demand_predictions,
                "current_efficiency": energy_optimizer._calculate_efficiency(data)
            }
        
        return jsonify({
            "timestamp": datetime.utcnow().isoformat(),
            "predictions": predictions
        })
        
    except Exception as e:
        logger.error(f"Predictions error: {e}")
        return jsonify({"message": "Failed to get predictions"}), 500

def calculate_system_metrics(sensor_data):
    """Calculate comprehensive system metrics"""
    if not sensor_data:
        return {}
    
    total_input = sum(zone.get("inputPower", 0) for zone in sensor_data.values())
    total_output = sum(zone.get("outputPower", 0) for zone in sensor_data.values())
    total_solar = sum(zone.get("solarGeneration", 0) for zone in sensor_data.values())
    avg_battery = sum(zone.get("batteryPercentage", 50) for zone in sensor_data.values()) / len(sensor_data)
    
    active_zones = sum(1 for zone_data in sensor_data.values() 
                      if zone_data.get("relayState", False))
    
    # Calculate efficiency
    system_efficiency = (total_output / total_input * 100) if total_input > 0 else 0
    
    # Calculate net energy flow
    net_energy = total_input + total_solar - total_output
    
    return {
        "total_input_power": round(total_input, 2),
        "total_output_power": round(total_output, 2),
        "total_solar_generation": round(total_solar, 2),
        "net_energy_flow": round(net_energy, 2),
        "average_battery_percentage": round(avg_battery, 2),
        "system_efficiency": round(system_efficiency, 2),
        "active_zones": active_zones,
        "total_zones": len(Config.ZONES),
        "energy_status": get_energy_status(avg_battery, net_energy)
    }

def get_energy_status(battery_level, net_energy):
    """Determine overall energy status"""
    if battery_level < Config.EMERGENCY_BATTERY_THRESHOLD:
        return "EMERGENCY"
    elif battery_level < Config.CRITICAL_BATTERY_THRESHOLD:
        return "CRITICAL"
    elif battery_level < Config.LOW_BATTERY_THRESHOLD:
        return "LOW"
    elif net_energy > 0:
        return "CHARGING"
    else:
        return "NORMAL"

def get_optimization_recommendations(sensor_data):
    """Get optimization recommendations without executing them"""
    try:
        # Run optimization in simulation mode
        result = energy_optimizer.optimize_energy_allocation(sensor_data)
        
        if result["success"]:
            return {
                "recommended_actions": result["decisions"],
                "reasoning": result["reasoning"],
                "system_state": result["system_state"]
            }
        else:
            return {"error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Optimization recommendations error: {e}")
        return {"error": str(e)}