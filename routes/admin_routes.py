from flask import Blueprint, request, jsonify
from services.firebase_service import get_document, set_document, query_collection
from core.decorators import role_required, log_api_call

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/control", methods=["POST"])
@log_api_call
@role_required("admin")
def control(user_data):
    """Control a zone relay (ON/OFF)"""
    data = request.get_json()
    zone = data.get("zone")
    action = data.get("action")

    if not zone or not action:
        return jsonify({"message": "Zone and action required"}), 400

    set_document("zones", zone, {"status": action})
    return jsonify({"message": f"Zone {zone} set to {action}"})


@admin_bp.route("/overview", methods=["GET"])
@log_api_call
@role_required("admin")
def overview(user_data):
    """Get system overview from Firebase"""
    households = query_collection("households")
    zones = query_collection("zones")
    alerts = query_collection("alerts", order_by="timestamp", limit=10)

    return jsonify({
        "households": households,
        "zones": zones,
        "recent_alerts": alerts
    })


@admin_bp.route("/optimize", methods=["POST"])
@log_api_call
@role_required("admin")
def optimize(user_data):
    """Trigger optimization manually"""
    # just flag in firebase for optimizer service
    set_document("system", "optimizer_trigger", {"status": "pending"})
    return jsonify({"message": "Optimization triggered"})


@admin_bp.route("/logs", methods=["GET"])
@log_api_call
@role_required("admin")
def logs(user_data):
    """Fetch audit logs"""
    logs = query_collection("logs", order_by="timestamp", limit=50)
    return jsonify({"logs": logs})


@admin_bp.route("/message", methods=["POST"])
@log_api_call
@role_required("admin")
def message(user_data):
    """Send message to household via Firebase"""
    data = request.get_json()
    household_id = data.get("household_id")
    message = data.get("message")

    if not household_id or not message:
        return jsonify({"message": "household_id and message required"}), 400

    set_document("households/{}/messages".format(household_id), "latest", {
        "from": user_data["id"],
        "message": message
    })
    return jsonify({"message": "Message sent"})
