from flask import Blueprint
from controllers.energy_controller import (
    energy_status, update_voltage, get_zone_history, 
    run_optimization, get_predictions
)
from core.decorators import role_required, log_api_call

energy_bp = Blueprint("energy", __name__)

@energy_bp.route("/status", methods=["GET"])
@log_api_call
def status():
    return energy_status()

@energy_bp.route("/updateVoltage", methods=["POST"])
def update_voltage_route():
    return update_voltage()

@energy_bp.route("/history", methods=["GET"])
@log_api_call
@role_required("admin", "household")
def history(user_data):
    return get_zone_history()

@energy_bp.route("/optimize", methods=["POST"])
@log_api_call
@role_required("admin")
def optimize(user_data):
    return run_optimization()

@energy_bp.route("/predictions", methods=["GET"])
@log_api_call
@role_required("admin")
def predictions(user_data):
    return get_predictions()