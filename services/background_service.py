"""
Background service for continuous monitoring and optimization
Runs periodic tasks using schedule
"""

import schedule
import time
import threading
import logging
from datetime import datetime
from services.firebase_service import get_sensor_data
from services.optimization_service import energy_optimizer
from services.notification_service import notification_service
from services.ml_service import ml_service
from config import Config

logger = logging.getLogger(__name__)

class BackgroundMonitor:
    def __init__(self):
        self.running = False
        self.last_battery_alert = None
        self.last_optimization = None
        
    def start(self):
        """Start background monitoring"""
        self.running = True
        
        # Schedule periodic tasks
        schedule.every(30).seconds.do(self.monitor_system)
        schedule.every(5).minutes.do(self.run_optimization)
        schedule.every(1).hours.do(self.retrain_models)
        
        # Start scheduler in separate thread
        scheduler_thread = threading.Thread(target=self._run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        logger.info("Background monitoring started")
    
    def stop(self):
        """Stop background monitoring"""
        self.running = False
        logger.info("Background monitoring stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def monitor_system(self):
        """Monitor system for emergencies and alerts"""
        try:
            sensor_data = get_sensor_data()
            if not sensor_data:
                return
            
            self._check_battery_levels(sensor_data)
            self._check_anomalies(sensor_data)
            self._check_zone_status(sensor_data)
            
        except Exception as e:
            logger.error(f"System monitoring error: {e}")
    
    def _check_battery_levels(self, sensor_data):
        """Check battery levels and send alerts"""
        for zone, data in sensor_data.items():
            battery_percentage = data.get("batteryPercentage", 50)
            
            if battery_percentage < Config.EMERGENCY_BATTERY_THRESHOLD:
                if zone in Config.ZONES and Config.ZONES[zone]["type"] == "critical":
                    notification_service.send_emergency_alert(
                        "CRITICAL_BATTERY_FAILURE",
                        f"Critical zone {zone} battery at {battery_percentage:.1f}%",
                        [zone]
                    )
            
            elif battery_percentage < Config.LOW_BATTERY_THRESHOLD:
                current_time = datetime.utcnow()
                if (not self.last_battery_alert or 
                    (current_time - self.last_battery_alert).seconds > 3600):
                    notification_service.send_low_battery_alert(
                        battery_percentage, 
                        [zone]
                    )
                    self.last_battery_alert = current_time
    
    def _check_anomalies(self, sensor_data):
        """Check for anomalies in energy data"""
        for zone, data in sensor_data.items():
            anomaly_result = ml_service.detect_anomaly(data)
            
            if anomaly_result["hasAnomaly"] and anomaly_result["severity"] == "HIGH":
                notification_service.send_emergency_alert(
                    "ENERGY_ANOMALY",
                    f"Anomaly detected in {zone}: {', '.join(anomaly_result['anomalies'])}",
                    [zone]
                )
    
    def _check_zone_status(self, sensor_data):
        """Check if critical zones are functioning"""
        for zone, config in Config.ZONES.items():
            if config["type"] == "critical":
                zone_data = sensor_data.get(zone, {})
                relay_state = zone_data.get("relayState", False)
                battery_level = zone_data.get("batteryPercentage", 0)
                
                if not relay_state and battery_level > Config.CRITICAL_BATTERY_THRESHOLD:
                    notification_service.send_emergency_alert(
                        "CRITICAL_ZONE_FAILURE",
                        f"Critical zone {zone} ({config['name']}) is offline with sufficient battery",
                        [zone]
                    )
    
    def run_optimization(self):
        """Run energy optimization"""
        try:
            current_time = datetime.utcnow()
            if (self.last_optimization and 
                (current_time - self.last_optimization).seconds < 300):
                return
            
            sensor_data = get_sensor_data()
            if not sensor_data:
                logger.warning("No sensor data available for optimization")
                return
            
            result = energy_optimizer.optimize_energy_allocation(sensor_data)
            
            if result["success"]:
                logger.info("Optimization completed successfully")
                self.last_optimization = current_time
            else:
                logger.error(f"Optimization failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Optimization error: {e}")
    
    def retrain_models(self):
        """Retrain ML models with recent data"""
        try:
            # 🔧 TODO: Replace with Firebase historical data fetch
            historical_data = []  
            
            if len(historical_data) > 100:
                success = ml_service.train_models(historical_data)
                if success:
                    logger.info("ML models retrained successfully")
                else:
                    logger.warning("ML model retraining failed")
            else:
                logger.info("Insufficient data for model retraining")
                
        except Exception as e:
            logger.error(f"Model retraining error: {e}")

# Global background monitor instance
background_monitor = BackgroundMonitor()

def start_background_tasks():
    """Initialize and start background tasks"""
    try:
        background_monitor.start()
    except Exception as e:
        logger.error(f"Failed to start background tasks: {e}")
