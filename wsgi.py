"""
WSGI entry point for production deployment
"""

from app import app
from services.background_service import start_background_tasks
from services.watchdog_service import start_watchdog
from services.emergency_service import start_emergency_service

if __name__ == "__main__":
    # Initialize all services
    start_background_tasks()
    start_watchdog()
    start_emergency_service()
    
    app.run()