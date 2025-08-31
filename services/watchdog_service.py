"""
Watchdog service to ensure system reliability
Monitors Firebase connections, retries failed commands, and maintains system health
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from services.firebase_service import get_sensor_data, set_command, get_all_zone_commands
from services.notification_service import notification_service
from config import Config

logger = logging.getLogger(__name__)

class WatchdogService:
    def __init__(self):
        self.running = False
        self.failed_commands = {}
        self.last_data_timestamp = {}
        self.connection_failures = 0
        
    def start(self):
        """Start watchdog monitoring"""
        self.running = True
        
        # Start watchdog thread
        watchdog_thread = threading.Thread(target=self._watchdog_loop)
        watchdog_thread.daemon = True
        watchdog_thread.start()
        
        logger.info("Watchdog service started")
    
    def stop(self):
        """Stop watchdog monitoring"""
        self.running = False
        logger.info("Watchdog service stopped")
    
    def _watchdog_loop(self):
        """Main watchdog monitoring loop"""
        while self.running:
            try:
                # Check Firebase connectivity
                self._check_firebase_connectivity()
                
                # Monitor command execution
                self._monitor_command_execution()
                
                # Check data freshness
                self._check_data_freshness()
                
                # Retry failed commands
                self._retry_failed_commands()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Watchdog loop error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _check_firebase_connectivity(self):
        """Check if Firebase is responding"""
        try:
            data = get_sensor_data()
            if data:
                self.connection_failures = 0
            else:
                self.connection_failures += 1
                
            # Alert if connection fails multiple times
            if self.connection_failures >= 3:
                logger.error("Firebase connectivity issues detected")
                notification_service.send_emergency_alert(
                    "FIREBASE_CONNECTION_FAILURE",
                    f"Firebase connection failed {self.connection_failures} times",
                    []
                )
                self.connection_failures = 0  # Reset to avoid spam
                
        except Exception as e:
            self.connection_failures += 1
            logger.error(f"Firebase connectivity check failed: {e}")
    
    def _monitor_command_execution(self):
        """Monitor if commands are being executed properly"""
        try:
            commands = get_all_zone_commands()
            current_time = time.time()
            
            for zone, command_data in commands.items():
                if isinstance(command_data, dict):
                    command_timestamp = command_data.get("timestamp", 0)
                    command = command_data.get("command")
                    
                    # If command is older than 2 minutes, consider it failed
                    if current_time - command_timestamp > 120:
                        logger.warning(f"Command timeout for {zone}: {command}")
                        self._handle_failed_command(zone, command, "TIMEOUT")
        
        except Exception as e:
            logger.error(f"Command monitoring error: {e}")
    
    def _check_data_freshness(self):
        """Check if sensor data is fresh"""
        try:
            sensor_data = get_sensor_data()
            current_time = datetime.utcnow()
            
            for zone, data in sensor_data.items():
                # Check if data has a timestamp
                data_timestamp = data.get("timestamp")
                if data_timestamp:
                    try:
                        data_time = datetime.fromisoformat(data_timestamp.replace('Z', '+00:00'))
                        age_minutes = (current_time - data_time).total_seconds() / 60
                        
                        # Alert if data is older than 10 minutes
                        if age_minutes > 10:
                            logger.warning(f"Stale data detected for {zone}: {age_minutes:.1f} minutes old")
                            
                            # Send alert for critical zones only
                            if Config.ZONES.get(zone, {}).get("type") == "critical":
                                notification_service.send_emergency_alert(
                                    "STALE_DATA_CRITICAL",
                                    f"Critical zone {zone} data is {age_minutes:.1f} minutes old",
                                    [zone]
                                )
                    except Exception as e:
                        logger.error(f"Error parsing timestamp for {zone}: {e}")
        
        except Exception as e:
            logger.error(f"Data freshness check error: {e}")
    
    def _retry_failed_commands(self):
        """Retry commands that failed previously"""
        current_time = time.time()
        zones_to_remove = []
        
        for zone, failure_data in self.failed_commands.items():
            # Retry after 5 minutes
            if current_time - failure_data["timestamp"] > 300:
                command = failure_data["command"]
                retry_count = failure_data.get("retry_count", 0)
                
                if retry_count < 3:  # Max 3 retries
                    logger.info(f"Retrying failed command: {zone} -> {command}")
                    success = set_command(zone, command)
                    
                    if success:
                        logger.info(f"Retry successful for {zone}")
                        zones_to_remove.append(zone)
                    else:
                        self.failed_commands[zone]["retry_count"] = retry_count + 1
                        self.failed_commands[zone]["timestamp"] = current_time
                else:
                    # Max retries reached
                    logger.error(f"Max retries reached for {zone}, giving up")
                    notification_service.send_emergency_alert(
                        "COMMAND_RETRY_FAILURE",
                        f"Failed to execute command for {zone} after 3 retries: {command}",
                        [zone]
                    )
                    zones_to_remove.append(zone)
        
        # Remove resolved or expired failures
        for zone in zones_to_remove:
            del self.failed_commands[zone]
    
    def _handle_failed_command(self, zone, command, reason):
        """Handle a failed command"""
        self.failed_commands[zone] = {
            "command": command,
            "reason": reason,
            "timestamp": time.time(),
            "retry_count": 0
        }
        
        logger.warning(f"Command failed for {zone}: {command} (Reason: {reason})")
    
    def get_watchdog_status(self):
        """Get current watchdog status"""
        return {
            "running": self.running,
            "connection_failures": self.connection_failures,
            "failed_commands": len(self.failed_commands),
            "failed_command_details": self.failed_commands
        }

# Global watchdog service instance
watchdog_service = WatchdogService()

def start_watchdog():
    """Start the watchdog service"""
    watchdog_service.start()

def stop_watchdog():
    """Stop the watchdog service"""
    watchdog_service.stop()