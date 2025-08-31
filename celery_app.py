"""
Celery configuration for background tasks
"""

from celery import Celery
from config import Config

def make_celery(app):
    """Create Celery instance"""
    celery = Celery(
        app.import_name,
        backend=Config.CELERY_RESULT_BACKEND,
        broker=Config.CELERY_BROKER_URL
    )
    
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Celery tasks
from celery import Celery
import logging

celery = Celery('microgrid')
celery.config_from_object(Config)

logger = logging.getLogger(__name__)

@celery.task
def optimize_energy_task():
    """Background task for energy optimization"""
    try:
        from services.firebase_service import get_sensor_data
        from services.optimization_service import energy_optimizer
        
        sensor_data = get_sensor_data()
        if sensor_data:
            result = energy_optimizer.optimize_energy_allocation(sensor_data)
            logger.info(f"Background optimization completed: {result['success']}")
            return result
        else:
            logger.warning("No sensor data available for background optimization")
            return {"success": False, "error": "No sensor data"}
            
    except Exception as e:
        logger.error(f"Background optimization task error: {e}")
        return {"success": False, "error": str(e)}

@celery.task
def retrain_models_task():
    """Background task for model retraining"""
    try:
        from services.ml_service import ml_service
        from services.database_service import get_energy_history
        from config import Config
        
        # Collect historical data from all zones
        historical_data = []
        for zone in Config.ZONES.keys():
            zone_history = get_energy_history(zone, hours=168)  # 7 days
            for record in zone_history:
                record["zone"] = zone
                historical_data.append(record)
        
        if len(historical_data) > 100:
            success = ml_service.train_models(historical_data)
            logger.info(f"Model retraining completed: {success}")
            return {"success": success}
        else:
            logger.info("Insufficient data for model retraining")
            return {"success": False, "error": "Insufficient data"}
            
    except Exception as e:
        logger.error(f"Model retraining task error: {e}")
        return {"success": False, "error": str(e)}

@celery.task
def send_daily_report_task():
    """Send daily energy report"""
    try:
        from services.notification_service import notification_service
        from services.database_service import get_energy_history
        from datetime import datetime, timedelta
        
        # Generate daily report
        yesterday = datetime.utcnow() - timedelta(days=1)
        report_data = {}
        
        for zone in Config.ZONES.keys():
            history = get_energy_history(zone, hours=24)
            if history:
                total_consumption = sum(h["outputPower"] for h in history if h["outputPower"])
                avg_battery = sum(h["batteryPercentage"] for h in history if h["batteryPercentage"]) / len(history)
                
                report_data[zone] = {
                    "total_consumption": total_consumption,
                    "avg_battery": avg_battery
                }
        
        # Send report
        report_message = f"Daily Energy Report - {yesterday.strftime('%Y-%m-%d')}\n"
        for zone, data in report_data.items():
            report_message += f"{zone}: {data['total_consumption']:.1f}W consumed, {data['avg_battery']:.1f}% avg battery\n"
        
        if Config.ADMIN_EMAIL:
            notification_service.send_email(
                Config.ADMIN_EMAIL,
                "Daily Energy Report",
                report_message
            )
        
        logger.info("Daily report sent successfully")
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Daily report task error: {e}")
        return {"success": False, "error": str(e)}