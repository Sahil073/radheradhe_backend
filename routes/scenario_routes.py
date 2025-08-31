from flask import Blueprint, request, jsonify
from controllers.scenario_controller import apply_scenarios
from services.firebase_service import get_sensor_data
from services.optimization_service import energy_optimizer
from core.decorators import role_required, log_api_call
from core.logger import log_action
import logging

logger = logging.getLogger(__name__)

scenario_bp = Blueprint("scenario", __name__)

@scenario_bp.route("/apply", methods=["POST"])
@log_api_call
@role_required("admin")
def apply(user_data):
    """Apply optimization scenarios"""
    try:
        data = get_sensor_data()
        if not data:
            return jsonify({"message": "No sensor data available"}), 404
        
        # Use the enhanced optimization service
        result = energy_optimizer.optimize_energy_allocation(data)
        
        log_action(
            user_data["id"],
            "Applied optimization scenario",
            extra_data={"result": result}
        )
        
        return jsonify({
            "message": "Scenario applied successfully",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Scenario application error: {e}")
        return jsonify({"message": "Failed to apply scenario"}), 500

@scenario_bp.route("/schedule", methods=["GET"])
@log_api_call
@role_required("admin")
def get_schedule(user_data):
    """Get optimization schedule"""
    try:
        hours = int(request.args.get("hours", 24))
        schedule = energy_optimizer.get_optimization_schedule(hours)
        
        return jsonify({
            "schedule": schedule,
            "hours_ahead": hours
        })
        
    except Exception as e:
        logger.error(f"Schedule error: {e}")
        return jsonify({"message": "Failed to get schedule"}), 500

@scenario_bp.route("/simulate", methods=["POST"])
@log_api_call
@role_required("admin")
def simulate(user_data):
    """Simulate optimization without executing"""
    try:
        data = request.get_json()
        
        # Use provided data or get current sensor data
        sensor_data = data.get("sensor_data") or get_sensor_data()
        
        if not sensor_data:
            return jsonify({"message": "No sensor data available"}), 404
        
        # Run optimization in simulation mode (don't execute commands)
        result = energy_optimizer.optimize_energy_allocation(sensor_data)
        
        # Remove execution results for simulation
        if "execution_results" in result:
            del result["execution_results"]
        
        log_action(
            user_data["id"],
            "Ran optimization simulation",
            extra_data={"simulation_result": result}
        )
        
        return jsonify({
            "message": "Simulation completed",
            "simulation_result": result
        })
        
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        return jsonify({"message": "Simulation failed"}), 500