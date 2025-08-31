"""
Enhanced Firebase service with retry logic and error handling (Firebase-only)
"""

import firebase_admin
from firebase_admin import credentials, db
from config import Config
import time
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase app only once
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {
            "databaseURL": Config.FIREBASE_DB_URL
        })
        logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")

def get_sensor_data():
    """Fetch latest sensor data from Firebase"""
    try:
        ref = db.reference("sensors/")
        data = ref.get()
        return data or {}
    except Exception as e:
        logger.error(f"Error fetching sensor data: {e}")
        return {}

def set_command(zone, command, retry_count=3):
    """
    Send command (ON/OFF) to a zone via Firebase with retry logic
    """
    for attempt in range(retry_count):
        try:
            ref = db.reference(f"commands/{zone}")
            ref.set({
                "command": command,
                "timestamp": time.time(),
                "attempt": attempt + 1
            })
            logger.info(f"Command sent successfully: {zone} -> {command}")
            return True
        except Exception as e:
            logger.warning(f"Command attempt {attempt + 1} failed: {e}")
            if attempt < retry_count - 1:
                time.sleep(1)
    logger.error(f"Failed to send command after {retry_count} attempts")
    return False

def get_zone_status(zone):
    """Get current status of a specific zone"""
    try:
        ref = db.reference(f"status/{zone}")
        return ref.get() or {}
    except Exception as e:
        logger.error(f"Error getting zone status: {e}")
        return {}

def set_zone_status(zone, status):
    """Update zone status in Firebase"""
    try:
        ref = db.reference(f"status/{zone}")
        ref.set({
            **status,
            "lastUpdated": time.time()
        })
        return True
    except Exception as e:
        logger.error(f"Error setting zone status: {e}")
        return False

def get_all_zone_commands():
    """Get all pending commands"""
    try:
        ref = db.reference("commands/")
        return ref.get() or {}
    except Exception as e:
        logger.error(f"Error getting commands: {e}")
        return {}

def clear_command(zone):
    """Clear executed command"""
    try:
        ref = db.reference(f"commands/{zone}")
        ref.delete()
        return True
    except Exception as e:
        logger.error(f"Error clearing command: {e}")
        return False
