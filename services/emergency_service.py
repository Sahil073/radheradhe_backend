"""
Enhanced emergency alert system with escalation procedures
"""

import logging
from datetime import datetime
from services.notification_service import notification_service
from services.firebase_service import set_command
from config import Config
from core.logger import log_emergency

logger = logging.getLogger(__name__)

class EmergencyService:
    def __init__(self):
        self.active_emergencies = {}
        
    def trigger_emergency_shutdown(self, reason, affected_zones=None):
        """
        Trigger emergency shutdown of non-critical zones
        """
        try:
            emergency_id = f"emergency_{int(datetime.utcnow().timestamp())}"
            
            # Shutdown non-critical zones
            shutdown_results = {}
            zones_to_shutdown = affected_zones or []
            
            if not zones_to_shutdown:
                # Shutdown all non-critical zones
                for zone, config in Config.ZONES.items():
                    if config["type"] in ["non-critical", "deferrable"]:
                        zones_to_shutdown.append(zone)
            
            for zone in zones_to_shutdown:
                success = set_command(zone, "OFF")
                shutdown_results[zone] = success
                
                if success:
                    logger.info(f"Emergency shutdown: {zone} turned OFF")
                else:
                    logger.error(f"Emergency shutdown failed for {zone}")
            
            # Log emergency
            emergency_data = {
                "id": emergency_id,
                "reason": reason,
                "affected_zones": zones_to_shutdown,
                "shutdown_results": shutdown_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.active_emergencies[emergency_id] = emergency_data
            log_emergency("EMERGENCY_SHUTDOWN", emergency_data)
            
            # Send alerts
            notification_service.send_emergency_alert(
                "EMERGENCY_SHUTDOWN",
                f"Emergency shutdown triggered: {reason}",
                zones_to_shutdown
            )
            
            return {
                "emergency_id": emergency_id,
                "zones_shutdown": zones_to_shutdown,
                "results": shutdown_results
            }
            
        except Exception as e:
            logger.error(f"Emergency shutdown error: {e}")
            return {"error": str(e)}
    
    def handle_critical_zone_failure(self, zone, failure_reason):
        """
        Handle failure of critical zones (hospital, emergency lights)
        """
        try:
            emergency_id = f"critical_failure_{int(datetime.utcnow().timestamp())}"
            
            # Immediate alert to all channels
            notification_service.send_emergency_alert(
                "CRITICAL_ZONE_FAILURE",
                f"CRITICAL: {Config.ZONES[zone]['name']} has failed - {failure_reason}",
                [zone]
            )
            
            # Try to restart the zone
            restart_success = set_command(zone, "ON")
            
            emergency_data = {
                "id": emergency_id,
                "zone": zone,
                "failure_reason": failure_reason,
                "restart_attempted": True,
                "restart_success": restart_success,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.active_emergencies[emergency_id] = emergency_data
            log_emergency("CRITICAL_ZONE_FAILURE", emergency_data)
            
            # If restart failed, escalate
            if not restart_success:
                self._escalate_critical_failure(zone, emergency_id)
            
            return emergency_data
            
        except Exception as e:
            logger.error(f"Critical zone failure handling error: {e}")
            return {"error": str(e)}
    
    def handle_battery_emergency(self, battery_level, affected_zones):
        """
        Handle battery emergency situations
        """
        try:
            emergency_id = f"battery_emergency_{int(datetime.utcnow().timestamp())}"
            
            # Implement emergency battery protocol
            if battery_level < Config.EMERGENCY_BATTERY_THRESHOLD:
                # Shutdown all non-critical zones immediately
                shutdown_result = self.trigger_emergency_shutdown(
                    f"Battery critical: {battery_level:.1f}%",
                    [zone for zone, config in Config.ZONES.items() 
                     if config["type"] in ["non-critical", "deferrable"]]
                )
                
                emergency_data = {
                    "id": emergency_id,
                    "type": "BATTERY_CRITICAL",
                    "battery_level": battery_level,
                    "affected_zones": affected_zones,
                    "shutdown_result": shutdown_result,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            elif battery_level < Config.CRITICAL_BATTERY_THRESHOLD:
                # Shutdown deferrable zones only
                shutdown_result = self.trigger_emergency_shutdown(
                    f"Battery low: {battery_level:.1f}%",
                    [zone for zone, config in Config.ZONES.items() 
                     if config["type"] == "deferrable"]
                )
                
                emergency_data = {
                    "id": emergency_id,
                    "type": "BATTERY_LOW",
                    "battery_level": battery_level,
                    "affected_zones": affected_zones,
                    "shutdown_result": shutdown_result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            self.active_emergencies[emergency_id] = emergency_data
            log_emergency("BATTERY_EMERGENCY", emergency_data)
            
            return emergency_data
            
        except Exception as e:
            logger.error(f"Battery emergency handling error: {e}")
            return {"error": str(e)}
    
    def _escalate_critical_failure(self, zone, emergency_id):
        """
        Escalate critical failures to higher authorities
        """
        try:
            # Send additional alerts
            escalation_message = f"ESCALATION: Critical zone {zone} ({Config.ZONES[zone]['name']}) restart failed. Manual intervention required immediately."
            
            # Send to multiple contacts if available
            if Config.ADMIN_PHONE:
                notification_service.send_sms(Config.ADMIN_PHONE, escalation_message, "EMERGENCY")
            
            if Config.ADMIN_EMAIL:
                notification_service.send_email(
                    Config.ADMIN_EMAIL,
                    "CRITICAL ESCALATION REQUIRED",
                    escalation_message,
                    "EMERGENCY"
                )
            
            # Update emergency record
            if emergency_id in self.active_emergencies:
                self.active_emergencies[emergency_id]["escalated"] = True
                self.active_emergencies[emergency_id]["escalation_time"] = datetime.utcnow().isoformat()
            
            logger.critical(f"Critical failure escalated for zone {zone}")
            
        except Exception as e:
            logger.error(f"Escalation error: {e}")
    
    def resolve_emergency(self, emergency_id, resolution_notes=""):
        """
        Mark emergency as resolved
        """
        try:
            if emergency_id in self.active_emergencies:
                self.active_emergencies[emergency_id]["resolved"] = True
                self.active_emergencies[emergency_id]["resolution_time"] = datetime.utcnow().isoformat()
                self.active_emergencies[emergency_id]["resolution_notes"] = resolution_notes
                
                logger.info(f"Emergency {emergency_id} resolved: {resolution_notes}")
                return True
            else:
                logger.warning(f"Emergency {emergency_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Emergency resolution error: {e}")
            return False
    
    def get_active_emergencies(self):
        """Get list of active emergencies"""
        active = {
            eid: data for eid, data in self.active_emergencies.items()
            if not data.get("resolved", False)
        }
        return active
    
    def get_emergency_history(self, hours=24):
        """Get emergency history"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_emergencies = {}
        for eid, data in self.active_emergencies.items():
            emergency_time = datetime.fromisoformat(data["timestamp"])
            if emergency_time >= cutoff_time:
                recent_emergencies[eid] = data
        
        return recent_emergencies

# Global emergency service instance
emergency_service = EmergencyService()

def start_emergency_service():
    """Start the emergency service"""
    emergency_service.start()

def stop_emergency_service():
    """Stop the emergency service"""
    emergency_service.stop()