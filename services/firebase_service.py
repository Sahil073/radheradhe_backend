"""
Comprehensive Firebase service with generic CRUD, query, and retry logic
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


# ---------------- Generic Document Functions ----------------
def get_document(path):
    """Fetch any document from Firebase by path"""
    try:
        ref = db.reference(path)
        return ref.get() or {}
    except Exception as e:
        logger.error(f"Error fetching document {path}: {e}")
        return {}


def set_document(path, data):
    """Set any document in Firebase by path"""
    try:
        ref = db.reference(path)
        ref.set({
            **data,
            "lastUpdated": time.time()
        })
        return True
    except Exception as e:
        logger.error(f"Error setting document {path}: {e}")
        return False


def add_document(path, data):
    """Add a new document to a Firebase collection with auto-generated key"""
    try:
        ref = db.reference(path)
        new_ref = ref.push(data)
        logger.info(f"Document added to {path} with key {new_ref.key}")
        return new_ref.key
    except Exception as e:
        logger.error(f"Error adding document to {path}: {e}")
        return None


def get_collection(path):
    """Fetch all documents from a Firebase collection"""
    try:
        ref = db.reference(path)
        return ref.get() or {}
    except Exception as e:
        logger.error(f"Error fetching collection {path}: {e}")
        return {}


def query_collection(path, filter_func=None):
    """
    Fetch all documents from a Firebase path and optionally filter them.
    :param filter_func: function to filter documents, receives (key, value)
    """
    try:
        data = get_collection(path)
        if filter_func:
            data = {k: v for k, v in data.items() if filter_func(k, v)}
        return data
    except Exception as e:
        logger.error(f"Error querying collection {path}: {e}")
        return {}


# ---------------- Sensor & Command Functions ----------------
def get_sensor_data():
    """Fetch latest sensor data from Firebase"""
    return get_document("sensors/")


def set_command(zone, command, retry_count=3):
    """
    Send command (ON/OFF) to a zone via Firebase with retry logic
    """
    for attempt in range(retry_count):
        try:
            path = f"commands/{zone}"
            set_document(path, {
                "command": command,
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
    return get_document(f"status/{zone}")


def set_zone_status(zone, status):
    """Update zone status in Firebase"""
    return set_document(f"status/{zone}", status)


def get_all_zone_commands():
    """Get all pending commands"""
    return get_document("commands/")


def clear_command(zone):
    """Clear executed command"""
    try:
        ref = db.reference(f"commands/{zone}")
        ref.delete()
        return True
    except Exception as e:
        logger.error(f"Error clearing command: {e}")
        return False
