from flask import Blueprint, request, jsonify
from services.firebase_service import get_document, query_collection, set_document
from core.decorators import role_required, log_api_call

household_bp = Blueprint("household", __name__)

@household_bp.route("/status", methods=["GET"])
@log_api_call
@role_required("household")
def status(user_data):
    household_id = user_data["id"]
    data = get_document("households", household_id)
    return jsonify({"household": data})


@household_bp.route("/control", methods=["POST"])
@log_api_call
@role_required("household")
def control(user_data):
    data = request.get_json()
    zone = data.get("zone")
    action = data.get("action")

    if not zone or not action:
        return jsonify({"message": "Zone and action required"}), 400

    set_document("zones", zone, {"status": action})
    return jsonify({"message": f"Zone {zone} set to {action}"})


@household_bp.route("/notifications", methods=["GET"])
@log_api_call
@role_required("household")
def notifications(user_data):
    household_id = user_data["id"]
    notifications = query_collection("households/{}/notifications".format(household_id), order_by="timestamp", limit=20)
    return jsonify({"notifications": notifications})


@household_bp.route("/notifications/read", methods=["POST"])
@log_api_call
@role_required("household")
def mark_read(user_data):
    data = request.get_json()
    notif_id = data.get("id")
    household_id = user_data["id"]

    if not notif_id:
        return jsonify({"message": "Notification ID required"}), 400

    set_document("households/{}/notifications".format(household_id), notif_id, {"status": "read"})
    return jsonify({"message": "Notification marked as read"})
