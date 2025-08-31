"""
Configuration file for Flask backend
Keeps all API keys, database URLs, and secrets in one place
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    
    # Firebase
    FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "")
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-key.json")
    
    # Database
    POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://localhost:5432/microgrid")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Twilio
    TWILIO_SID = os.getenv("TWILIO_SID", "")
    TWILIO_AUTH = os.getenv("TWILIO_AUTH", "")
    TWILIO_PHONE = os.getenv("TWILIO_PHONE", "")
    
    # Admin contacts
    ADMIN_PHONE = os.getenv("ADMIN_PHONE", "")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
    
    # Celery
    CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Zone Configuration
    ZONES = {
        "Zone1": {"type": "critical", "priority": 1, "name": "Hospital/Emergency"},
        "Zone2": {"type": "semi-critical", "priority": 2, "name": "Street Lights"},
        "Zone3": {"type": "non-critical", "priority": 3, "name": "Entertainment"},
        "Zone4": {"type": "deferrable", "priority": 4, "name": "Water Pumps"}
    }
    
    # Battery thresholds
    CRITICAL_BATTERY_THRESHOLD = 10  # %
    LOW_BATTERY_THRESHOLD = 20  # %
    EMERGENCY_BATTERY_THRESHOLD = 5  # %