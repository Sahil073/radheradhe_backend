from flask import Blueprint, request, jsonify
from services.firebase_service import get_document, set_document, query_collection, add_document
from core.decorators import role_required, log_api_call
import time

energy_bp = Blueprint("energy", __name__)

@energy_bp.route("/status", methods=["GET"])
@log_api_call
def status():
    zones = query_collection("zones")
    return jsonify({"zones": zones})


@energy_bp.route("/updateVoltage", methods=["POST"])
def update_voltage_route():
    data = request.get_json()
    zone = data.get("zone")
    voltage = data.get("voltage")

    if not zone or voltage is None:
        return jsonify({"message": "Zone and voltage required"}), 400

    set_document("zones", zone, {"voltage": voltage})
    return jsonify({"message": "Voltage updated"})


@energy_bp.route("/history", methods=["GET"])
@log_api_call
@role_required("admin", "household")
def history(user_data):
    zone = request.args.get("zone")
    filters = [("zone", "==", zone)] if zone else []
    history = query_collection("energy_history", filters=filters, order_by="timestamp", limit=100)
    return jsonify({"history": history})


@energy_bp.route("/optimize", methods=["POST"])
@log_api_call
@role_required("admin")
def optimize(user_data):
    set_document("system", "optimizer_trigger", {"status": "pending"})
    return jsonify({"message": "Optimization started"})


@energy_bp.route("/predictions", methods=["GET"])
@log_api_call
@role_required("admin")
def predictions(user_data):
    predictions = query_collection("predictions", order_by="timestamp", limit=10)
    return jsonify({"predictions": predictions})
