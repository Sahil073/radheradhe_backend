"""
Enhanced Household Controller with detailed energy insights
"""

from flask import request, jsonify
from services.firebase_service import get_sensor_data, set_command
from services.ml_service import ml_service
from services.database_service import get_energy_history
from core.logger import log_action
from config import Config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_household_data(user):
    """Get comprehensive household energy data"""
    try:
        household_id = user.get("householdId")
        if not household_id:
            return jsonify({"message": "No household ID associated with user"}), 400
        
        # Get current sensor data
        all_sensor_data = get_sensor_data()
        
        # Filter data for this household (assuming zone mapping)
        # In a real system, you'd have a mapping between households and zones
        household_zones = get_household_zones(household_id)
        
        household_data = {}
        for zone in household_zones:
            if zone in all_sensor_data:
                zone_data = all_sensor_data[zone]
                
                # Add predictions and analysis
                sustain_hours = ml_service.predict_battery_sustain(zone_data)
                anomaly_result = ml_service.detect_anomaly(zone_data)
                
                household_data[zone] = {
                    "current_data": zone_data,
                    "zone_info": Config.ZONES.get(zone, {}),
                    "sustain_hours": sustain_hours,
                    "anomaly": anomaly_result,
                    "status": get_zone_status_description(zone_data)
                }
        
        # Get recent history
        history_summary = get_household_history_summary(household_zones)
        
        # Calculate household metrics
        household_metrics = calculate_household_metrics(household_data)
        
        return jsonify({
            "household_id": household_id,
            "timestamp": datetime.utcnow().isoformat(),
            "zones": household_data,
            "metrics": household_metrics,
            "history_summary": history_summary,
            "recommendations": get_household_recommendations(household_data)
        })
        
    except Exception as e:
        logger.error(f"Household data error: {e}")
        return jsonify({"message": "Failed to get household data"}), 500

def limited_zone_control(user):
    """Allow household limited control over non-critical zones"""
    try:
        data = request.get_json()
        zone = data.get("zone")
        action = data.get("action")
        
        if not zone or not action:
            return jsonify({"message": "Zone and action required"}), 400
        
        if action not in ["ON", "OFF"]:
            return jsonify({"message": "Action must be ON or OFF"}), 400
        
        # Check if household can control this zone
        household_id = user.get("householdId")
        household_zones = get_household_zones(household_id)
        
        if zone not in household_zones:
            return jsonify({"message": "You don't have access to this zone"}), 403
        
        # Check zone type - households can't control critical zones
        zone_config = Config.ZONES.get(zone, {})
        if zone_config.get("type") == "critical":
            return jsonify({"message": "Cannot control critical zones"}), 403
        
        # Check system constraints
        if action == "ON":
            # Check if turning ON this zone would cause issues
            sensor_data = get_sensor_data()
            zone_data = sensor_data.get(zone, {})
            battery_level = zone_data.get("batteryPercentage", 0)
            
            if battery_level < Config.LOW_BATTERY_THRESHOLD:
                return jsonify({
                    "message": "Cannot turn ON zone due to low battery",
                    "battery_level": battery_level
                }), 400
        
        # Execute command
        success = set_command(zone, action)
        
        if success:
            log_action(
                user["id"],
                f"Household control: Set {zone} to {action}",
                zone,
                extra_data={"household_id": household_id}
            )
            
            return jsonify({
                "message": f"Zone {zone} set to {action}",
                "zone": zone,
                "action": action
            })
        else:
            return jsonify({"message": "Failed to execute command"}), 500
            
    except Exception as e:
        logger.error(f"Household zone control error: {e}")
        return jsonify({"message": "Internal server error"}), 500

def get_household_notifications(user):
    """Get notifications for household"""
    try:
        household_id = user.get("householdId")
        
        from services.firebase_service import db
        ref = db.reference(f"notifications/household_{household_id}")
        notifications = ref.get() or {}
        
        # Convert to list and sort by timestamp
        notification_list = []
        for key, notification in notifications.items():
            notification["id"] = key
            notification_list.append(notification)
        
        # Sort by timestamp (newest first)
        notification_list.sort(
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )
        
        return jsonify({
            "household_id": household_id,
            "notifications": notification_list[:50]  # Last 50 notifications
        })
        
    except Exception as e:
        logger.error(f"Household notifications error: {e}")
        return jsonify({"message": "Failed to get notifications"}), 500

def mark_notification_read(user):
    """Mark notification as read"""
    try:
        data = request.get_json()
        notification_id = data.get("notification_id")
        
        if not notification_id:
            return jsonify({"message": "Notification ID required"}), 400
        
        household_id = user.get("householdId")
        
        from services.firebase_service import db
        ref = db.reference(f"notifications/household_{household_id}/{notification_id}")
        ref.update({"read": True})
        
        return jsonify({"message": "Notification marked as read"})
        
    except Exception as e:
        logger.error(f"Mark notification read error: {e}")
        return jsonify({"message": "Failed to mark notification as read"}), 500

def get_household_zones(household_id):
    """Get zones associated with a household"""
    # This is a simplified mapping - in a real system, this would be in the database
    household_zone_mapping = {
        "H001": ["Zone2", "Zone3", "Zone4"],  # House 1 can control non-critical zones
        "H002": ["Zone3", "Zone4"],
        "H003": ["Zone4"]
    }
    
    return household_zone_mapping.get(household_id, [])

def calculate_household_metrics(household_data):
    """Calculate metrics specific to household"""
    if not household_data:
        return {}
    
    total_consumption = sum(
        zone["current_data"].get("outputPower", 0) 
        for zone in household_data.values()
    )
    
    total_generation = sum(
        zone["current_data"].get("inputPower", 0) + zone["current_data"].get("solarGeneration", 0)
        for zone in household_data.values()
    )
    
    avg_battery = sum(
        zone["current_data"].get("batteryPercentage", 50)
        for zone in household_data.values()
    ) / len(household_data)
    
    active_zones = sum(
        1 for zone in household_data.values()
        if zone["current_data"].get("relayState", False)
    )
    
    return {
        "total_consumption": round(total_consumption, 2),
        "total_generation": round(total_generation, 2),
        "net_energy": round(total_generation - total_consumption, 2),
        "average_battery": round(avg_battery, 2),
        "active_zones": active_zones,
        "total_zones": len(household_data),
        "efficiency": round((total_consumption / total_generation * 100) if total_generation > 0 else 0, 2)
    }

def get_household_history_summary(zones, hours=24):
    """Get summarized history for household zones"""
    try:
        summary = {}
        
        for zone in zones:
            history = get_energy_history(zone, hours)
            if history:
                # Calculate summary statistics
                consumption_values = [h["outputPower"] for h in history if h["outputPower"]]
                battery_values = [h["batteryPercentage"] for h in history if h["batteryPercentage"]]
                
                summary[zone] = {
                    "data_points": len(history),
                    "avg_consumption": round(sum(consumption_values) / len(consumption_values), 2) if consumption_values else 0,
                    "max_consumption": round(max(consumption_values), 2) if consumption_values else 0,
                    "min_battery": round(min(battery_values), 2) if battery_values else 0,
                    "avg_battery": round(sum(battery_values) / len(battery_values), 2) if battery_values else 0
                }
        
        return summary
        
    except Exception as e:
        logger.error(f"Household history summary error: {e}")
        return {}

def get_zone_status_description(zone_data):
    """Get human-readable status description"""
    relay_state = zone_data.get("relayState", False)
    battery_level = zone_data.get("batteryPercentage", 0)
    
    if not relay_state:
        return "OFF"
    elif battery_level < Config.CRITICAL_BATTERY_THRESHOLD:
        return "ON (Low Battery)"
    elif battery_level < Config.LOW_BATTERY_THRESHOLD:
        return "ON (Battery Warning)"
    else:
        return "ON (Normal)"

def get_household_recommendations(household_data):
    """Get energy saving recommendations for household"""
    recommendations = []
    
    for zone, data in household_data.items():
        zone_info = data["zone_info"]
        current_data = data["current_data"]
        efficiency = data.get("efficiency", 0)
        
        # Low efficiency recommendation
        if efficiency < 0.6 and current_data.get("relayState", False):
            recommendations.append({
                "type": "efficiency",
                "zone": zone,
                "message": f"Consider turning OFF {zone_info.get('name', zone)} - low efficiency detected",
                "priority": "MEDIUM"
            })
        
        # High consumption recommendation
        output_power = current_data.get("outputPower", 0)
        if output_power > 50:  # High consumption threshold
            recommendations.append({
                "type": "consumption",
                "zone": zone,
                "message": f"High power consumption in {zone_info.get('name', zone)} ({output_power}W)",
                "priority": "LOW"
            })
        
        # Battery-based recommendations
        battery_level = current_data.get("batteryPercentage", 50)
        if battery_level < Config.LOW_BATTERY_THRESHOLD and zone_info.get("type") in ["non-critical", "deferrable"]:
            recommendations.append({
                "type": "battery_conservation",
                "zone": zone,
                "message": f"Consider deferring {zone_info.get('name', zone)} usage until battery recovers",
                "priority": "HIGH"
            })
    
    return recommendations