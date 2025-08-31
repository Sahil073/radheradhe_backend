from flask import Blueprint, request, jsonify
from services.firebase_service import get_document, set_document
import uuid, time

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login_route():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = get_document("users", username)
    if not user or user.get("password") != password:
        return jsonify({"message": "Invalid credentials"}), 401

    token = str(uuid.uuid4())
    set_document("sessions", token, {"user": username, "created": time.time()})

    return jsonify({"token": token, "user": user})


@auth_bp.route("/refresh", methods=["POST"])
def refresh_route():
    data = request.get_json()
    old_token = data.get("token")
    if not old_token:
        return jsonify({"message": "Token required"}), 400

    new_token = str(uuid.uuid4())
    set_document("sessions", new_token, {"refreshed_from": old_token, "created": time.time()})
    return jsonify({"token": new_token})


@auth_bp.route("/logout", methods=["POST"])
def logout_route():
    data = request.get_json()
    token = data.get("token")
    if not token:
        return jsonify({"message": "Token required"}), 400

    set_document("sessions", token, {"status": "logged_out"})
    return jsonify({"message": "Logged out"})


@auth_bp.route("/profile", methods=["GET"])
def profile_route():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"message": "Unauthorized"}), 401

    session = get_document("sessions", token)
    if not session:
        return jsonify({"message": "Session not found"}), 404

    user = get_document("users", session["user"])
    return jsonify({"user": user})
