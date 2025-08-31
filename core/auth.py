"""
Enhanced JWT authentication with role-based access control
"""

import jwt
from datetime import datetime, timedelta
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import check_password_hash, generate_password_hash

def generate_tokens(user):
    """Generate access and refresh tokens for a user"""
    additional_claims = {
        "role": user["role"],
        "householdId": user.get("householdId")
    }
    
    access_token = create_access_token(
        identity=user["id"],
        additional_claims=additional_claims
    )
    
    refresh_token = create_refresh_token(identity=user["id"])
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    }

def verify_password(stored_password, provided_password):
    """Verify password hash"""
    return check_password_hash(stored_password, provided_password)

def hash_password(password):
    """Hash password for storage"""
    return generate_password_hash(password)

def decode_token(token):
    """Decode JWT token and return payload if valid"""
    try:
        return jwt.decode(
            token, 
            current_app.config["JWT_SECRET_KEY"], 
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}