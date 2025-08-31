from flask import Blueprint
from controllers.auth_controller import login, refresh_token, logout, get_profile

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login_route():
    return login()

@auth_bp.route("/refresh", methods=["POST"])
def refresh_route():
    return refresh_token()

@auth_bp.route("/logout", methods=["POST"])
def logout_route():
    return logout()

@auth_bp.route("/profile", methods=["GET"])
def profile_route():
    return get_profile()