from flask import Blueprint, request, jsonify
from services.notification_service import notification_service
from services.database_service import get_db_connection
from core.decorators import role_required, log_api_call
from core.logger import log_action
import logging

logger = logging.getLogger(__name__)

alert_bp = Blueprint("alerts", __name__)

@alert_bp.route("/history", methods=["GET"])
@log_api_call
@role_required("admin")
def get_alert_history(user_data):
    """Get alert history"""
    try:
        limit = int(request.args.get("limit", 50))
        severity = request.args.get("severity")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        
        query = """
            SELECT id, timestamp, alert_type, severity, message, recipient, status, zone
            FROM alerts
        """
        params = []
        
        if severity:
            query += " WHERE severity = %s"
            params.append(severity)
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        alerts = [{
            "id": row[0],
            "timestamp": row[1].isoformat(),
            "alert_type": row[2],
            "severity": row[3],
            "message": row[4],
            "recipient": row[5],
            "status": row[6],
            "zone": row[7]
        } for row in rows]
        
        return jsonify({"alerts": alerts})
        
    except Exception as e:
        logger.error(f"Get alert history error: {e}")
        return jsonify({"message": "Failed to get alert history"}), 500

@alert_bp.route("/send", methods=["POST"])
@log_api_call
@role_required("admin")
def send_custom_alert(user_data):
    """Send custom alert"""
    try:
        data = request.get_json()
        
        alert_type = data.get("type", "CUSTOM")
        message = data.get("message")
        recipient = data.get("recipient")
        channel = data.get("channel", "SMS")  # SMS, EMAIL, FIREBASE
        severity = data.get("severity", "NORMAL")
        
        if not message:
            return jsonify({"message": "Message required"}), 400
        
        success = False
        
        if channel == "SMS" and recipient:
            success = notification_service.send_sms(recipient, message, severity)
        elif channel == "EMAIL" and recipient:
            success = notification_service.send_email(
                recipient, 
                f"Alert: {alert_type}", 
                message, 
                severity
            )
        elif channel == "FIREBASE" and recipient:
            success = notification_service.send_firebase_notification(
                recipient,
                f"Alert: {alert_type}",
                message,
                {"type": "custom_alert", "severity": severity}
            )
        else:
            return jsonify({"message": "Invalid channel or missing recipient"}), 400
        
        if success:
            log_action(
                user_data["id"],
                f"Sent custom alert via {channel}",
                extra_data={
                    "recipient": recipient,
                    "message": message,
                    "severity": severity
                }
            )
            return jsonify({"message": "Alert sent successfully"})
        else:
            return jsonify({"message": "Failed to send alert"}), 500
            
    except Exception as e:
        logger.error(f"Send custom alert error: {e}")
        return jsonify({"message": "Internal server error"}), 500

@alert_bp.route("/emergency", methods=["POST"])
@log_api_call
@role_required("admin")
def trigger_emergency_alert(user_data):
    """Trigger emergency alert"""
    try:
        data = request.get_json()
        
        emergency_type = data.get("type", "MANUAL_EMERGENCY")
        details = data.get("details", "Manual emergency triggered by admin")
        affected_zones = data.get("zones", [])
        
        results = notification_service.send_emergency_alert(
            emergency_type,
            details,
            affected_zones
        )
        
        log_action(
            user_data["id"],
            f"Triggered emergency alert: {emergency_type}",
            extra_data={
                "details": details,
                "zones": affected_zones,
                "results": results
            }
        )
        
        return jsonify({
            "message": "Emergency alert sent",
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Emergency alert error: {e}")
        return jsonify({"message": "Failed to send emergency alert"}), 500