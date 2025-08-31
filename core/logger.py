"""
Enhanced audit logging system with structured logging
"""

import json
import logging
from datetime import datetime
from services.database_service import log_to_database

# Configure logger
logger = logging.getLogger(__name__)

def log_action(user_id, action, zone=None, extra_data=None):
    """
    Enhanced logging with structured data
    Logs to both file and database
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "action": action,
        "zone": zone,
        "extra_data": extra_data or {}
    }
    
    # Log to file
    logger.info(f"Action: {json.dumps(log_entry)}")
    
    # Log to database for querying
    try:
        log_to_database(log_entry)
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")

def log_energy_decision(decision_data):
    """Log optimization decisions"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": "energy_decision",
        "decision": decision_data
    }
    
    logger.info(f"Energy Decision: {json.dumps(log_entry)}")
    
    try:
        log_to_database(log_entry)
    except Exception as e:
        logger.error(f"Failed to log energy decision: {e}")

def log_emergency(emergency_type, details):
    """Log emergency events"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": "emergency",
        "emergency_type": emergency_type,
        "details": details,
        "severity": "HIGH"
    }
    
    logger.critical(f"Emergency: {json.dumps(log_entry)}")
    
    try:
        log_to_database(log_entry)
    except Exception as e:
        logger.error(f"Failed to log emergency: {e}")