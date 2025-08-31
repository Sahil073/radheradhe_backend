from flask import Blueprint, request
from controllers.admin_controller import (
    control_zone, get_system_overview, force_optimization, 
    get_audit_logs, send_message_to_household
)
from core.decorators import role_required, log_api_call

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/control", methods=["POST"])
@log_api_call
@role_required("admin")
def control(user_data):
    data = request.get_json()
    return control_zone(user_data, data.get("zone"), data.get("action"))

@admin_bp.route("/overview", methods=["GET"])
@log_api_call
@role_required("admin")
def overview(user_data):
    return get_system_overview(user_data)

@admin_bp.route("/optimize", methods=["POST"])
@log_api_call
@role_required("admin")
def optimize(user_data):
    return force_optimization(user_data)

@admin_bp.route("/logs", methods=["GET"])
@log_api_call
@role_required("admin")
def logs(user_data):
    return get_audit_logs(user_data)

@admin_bp.route("/message", methods=["POST"])
@log_api_call
@role_required("admin")
def message(user_data):
    return send_message_to_household(user_data)