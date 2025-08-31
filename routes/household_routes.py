from flask import Blueprint
from controllers.household_controller import (
    get_household_data, limited_zone_control, 
    get_household_notifications, mark_notification_read
)
from core.decorators import role_required, log_api_call

household_bp = Blueprint("household", __name__)

@household_bp.route("/status", methods=["GET"])
@log_api_call
@role_required("household")
def status(user_data):
    return get_household_data(user_data)

@household_bp.route("/control", methods=["POST"])
@log_api_call
@role_required("household")
def control(user_data):
    return limited_zone_control(user_data)

@household_bp.route("/notifications", methods=["GET"])
@log_api_call
@role_required("household")
def notifications(user_data):
    return get_household_notifications(user_data)

@household_bp.route("/notifications/read", methods=["POST"])
@log_api_call
@role_required("household")
def mark_read(user_data):
    return mark_notification_read(user_data)