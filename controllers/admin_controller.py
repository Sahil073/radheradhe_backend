"""
Enhanced Admin Controller with comprehensive zone control and system management
"""

from flask import request, jsonify
from services.firebase_service import set_command, get_sensor_data
from services.optimization_service import energy_optimizer
from services.notification_service import notification_service
from core.logger import log_action
from config import Config
import logging

logger = logging.getLogger(__name__)

def control_zone(user, zone, action):
    """Enhanced zone control with validation and logging"""
    try:
        # Validate inputs
        if not zone or not action:
            return jsonify({"message": "Zone and action required"}), 400
            
        if zone not in Config.ZONES:
            return jsonify({"message": "Invalid zone"}), 400
            
        if action not in ["ON", "OFF"]:
            return jsonify({"message": "Action must be ON or OFF"}), 400
        
        # Check if this is a critical zone being turned OFF
        zone_config = Config.ZONES[zone]
        if zone_config["type"] == "critical" and action == "OFF":
            # Get current battery level
            sensor_data = get_sensor_data()
            zone_data = sensor_data.get(zone, {})
            battery_level = zone_data.get("batteryPercentage", 0)
            
            if battery_level > Config.CRITICAL_BATTERY_THRESHOLD:
                logger.warning(f"Admin turning OFF critical zone {zone} with sufficient battery")
                # Send alert but allow the action
                notification_service.send_firebase_notification(
                    user["id"],
                    "Critical Zone Override",
                    f"You turned OFF critical zone {zone} with {battery_level:.1f}% battery",
                    {"type": "critical_override", "zone": zone}
                )
        
        # Execute command
        success = set_command(zone, action)
        
        if success:
            log_action(
                user["id"], 
                f"Admin override: Set {zone} to {action}",
                zone,
                extra_data={"zone_type": zone_config["type"]}
            )
            
            return jsonify({
                "message": f"Zone {zone} set to {action}",
                "zone": zone,
                "action": action,
                "zone_info": zone_config
            })
        else:
            return jsonify({"message": "Failed to execute command"}), 500
            
    except Exception as e:
        logger.error(f"Zone control error: {e}")
        return jsonify({"message": "Internal server error"}), 500

def get_system_overview(user):
    """Get comprehensive system overview for admin"""
    try:
        sensor_data = get_sensor_data()
        
        # Calculate system metrics
        total_zones = len(Config.ZONES)
        active_zones = sum(1 for zone_data in sensor_data.values() 
                          if zone_data.get("relayState", False))
        
        total_input = sum(zone.get("inputPower", 0) for zone in sensor_data.values())
        total_output = sum(zone.get("outputPower", 0) for zone in sensor_data.values())
        avg_battery = sum(zone.get("batteryPercentage", 50) for zone in sensor_data.values()) / len(sensor_data) if sensor_data else 0
        
        # Get optimization schedule
        schedule = energy_optimizer.get_optimization_schedule(24)
        
        # Zone status with priorities
        zone_status = {}
        for zone, config in Config.ZONES.items():
            zone_data = sensor_data.get(zone, {})
            zone_status[zone] = {
                **config,
                "current_data": zone_data,
                "efficiency": energy_optimizer._calculate_efficiency(zone_data),
                "sustain_hours": ml_service.predict_battery_sustain(zone_data)
            }
        
        return jsonify({
            "system_metrics": {
                "total_zones": total_zones,
                "active_zones": active_zones,
                "total_input_power": total_input,
                "total_output_power": total_output,
                "average_battery": avg_battery,
                "system_efficiency": (total_output / total_input * 100) if total_input > 0 else 0
            },
            "zone_status": zone_status,
            "optimization_schedule": schedule[:6],  # Next 6 hours
            "last_updated": sensor_data
        })
        
    except Exception as e:
        logger.error(f"System overview error: {e}")
        return jsonify({"message": "Failed to get system overview"}), 500

def force_optimization(user):
    """Force immediate optimization run"""
    try:
        sensor_data = get_sensor_data()
        if not sensor_data:
            return jsonify({"message": "No sensor data available"}), 404
        
        result = energy_optimizer.optimize_energy_allocation(sensor_data)
        
        log_action(
            user["id"],
            "Forced optimization run",
            extra_data={"result": result}
        )
        
        return jsonify({
            "message": "Optimization completed",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Force optimization error: {e}")
        return jsonify({"message": "Optimization failed"}), 500

def get_audit_logs(user):
    """Get audit logs for admin review"""
    try:
        from services.database_service import get_db_connection
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, user_id, action, zone, extra_data
            FROM audit_logs
            ORDER BY timestamp DESC
            LIMIT 100
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logs = [{
            "timestamp": row[0].isoformat(),
            "user_id": row[1],
            "action": row[2],
            "zone": row[3],
            "extra_data": row[4]
        } for row in rows]
        
        return jsonify({"logs": logs})
        
    except Exception as e:
        logger.error(f"Audit logs error: {e}")
        return jsonify({"message": "Failed to get audit logs"}), 500

def send_message_to_household(user):
    """Send message to specific household"""
    try:
        data = request.get_json()
        household_id = data.get("householdId")
        message = data.get("message")
        
        if not household_id or not message:
            return jsonify({"message": "Household ID and message required"}), 400
        
        success = notification_service.send_admin_message_to_household(household_id, message)
        
        if success:
            log_action(
                user["id"],
                f"Sent message to household {household_id}",
                extra_data={"message": message}
            )
            return jsonify({"message": "Message sent successfully"})
        else:
            return jsonify({"message": "Failed to send message"}), 500
            
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return jsonify({"message": "Internal server error"}), 500