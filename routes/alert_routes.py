from flask import Blueprint, request, jsonify
from services.firebase_service import query_collection, add_document
from core.decorators import role_required, log_api_call
from core.logger import log_action
import logging

logger = logging.getLogger(__name__)
alert_bp = Blueprint("alerts", __name__)

@alert_bp.route("/history", methods=["GET"])
@log_api_call
@role_required("admin")
def get_alert_history(user_data):
    """Get alert history from Firebase"""
    try:
        limit = int(request.args.get("limit", 50))
        severity = request.args.get("severity")

        filters = [("severity", "==", severity)] if severity else []
        alerts = query_collection("alerts", filters=filters, order_by="timestamp", limit=limit)

        return jsonify({"alerts": alerts})

    except Exception as e:
        logger.error(f"Get alert history error: {e}")
        return jsonify({"message": "Failed to get alert history"}), 500


@alert_bp.route("/send", methods=["POST"])
@log_api_call
@role_required("admin")
def send_custom_alert(user_data):
    """Send custom alert (store in Firebase)"""
    try:
        data = request.get_json()
        alert_type = data.get("type", "CUSTOM")
        message = data.get("message")
        recipient = data.get("recipient")
        severity = data.get("severity", "NORMAL")

        if not message or not recipient:
            return jsonify({"message": "Message and recipient required"}), 400

        add_document("alerts", {
            "alert_type": alert_type,
            "message": message,
            "recipient": recipient,
            "severity": severity,
            "status": "sent"
        })

        log_action(user_data["id"], f"Sent custom alert to {recipient}")
        return jsonify({"message": "Alert sent successfully"})

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

        add_document("alerts", {
            "alert_type": emergency_type,
            "message": details,
            "severity": "CRITICAL",
            "zones": affected_zones,
            "status": "emergency"
        })

        log_action(user_data["id"], f"Emergency alert: {emergency_type}")
        return jsonify({"message": "Emergency alert sent"})

    except Exception as e:
        logger.error(f"Emergency alert error: {e}")
        return jsonify({"message": "Failed to send emergency alert"}), 500
