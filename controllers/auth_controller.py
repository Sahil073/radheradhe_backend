"""
Enhanced Authentication Controller with secure login and user management
"""

from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from services.database_service import get_user_by_email, get_user_by_id
from core.auth import generate_tokens
from core.logger import log_action
import logging

logger = logging.getLogger(__name__)

def login():
    """Enhanced login API with proper security"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided"}), 400
            
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        
        if not email or not password:
            return jsonify({"message": "Email and password required"}), 400
        
        # Get user from database
        user = get_user_by_email(email)
        if not user:
            log_action("unknown", f"Failed login attempt for {email}", extra_data={"ip": request.remote_addr})
            return jsonify({"message": "Invalid credentials"}), 401
        
        # Verify password
        if not check_password_hash(user["password_hash"], password):
            log_action(user["id"], f"Failed login attempt", extra_data={"ip": request.remote_addr})
            return jsonify({"message": "Invalid credentials"}), 401
        
        # Generate tokens
        tokens = generate_tokens(user)
        
        # Update last login
        from services.database_service import get_db_connection
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
                """, (user["id"],))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                logger.error(f"Error updating last login: {e}")
        
        log_action(user["id"], "Successful login", extra_data={"ip": request.remote_addr})
        
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "householdId": user.get("householdId")
            },
            **tokens
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"message": "Internal server error"}), 500

@jwt_required()
def refresh_token():
    """Refresh access token"""
    try:
        current_user_id = get_jwt_identity()
        user = get_user_by_id(current_user_id)
        
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        tokens = generate_tokens(user)
        
        log_action(user["id"], "Token refreshed")
        
        return jsonify({
            "message": "Token refreshed",
            **tokens
        })
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({"message": "Token refresh failed"}), 500

@jwt_required()
def logout():
    """Logout user (client should discard tokens)"""
    try:
        current_user_id = get_jwt_identity()
        log_action(current_user_id, "User logged out")
        
        return jsonify({"message": "Logged out successfully"})
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"message": "Logout failed"}), 500

@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        current_user_id = get_jwt_identity()
        user = get_user_by_id(current_user_id)
        
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        return jsonify({
            "user": {
                "id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "householdId": user.get("householdId")
            }
        })
        
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        return jsonify({"message": "Failed to get profile"}), 500