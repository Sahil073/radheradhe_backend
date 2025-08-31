from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
import logging
from datetime import datetime

# Initialize app
app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

# Initialize JWT
jwt = JWTManager(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Import routes
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.household_routes import household_bp
from routes.energy_routes import energy_bp
from routes.scenario_routes import scenario_bp
from routes.alert_routes import alert_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(household_bp, url_prefix="/api/household")
app.register_blueprint(energy_bp, url_prefix="/api/energy")
app.register_blueprint(scenario_bp, url_prefix="/api/scenario")
app.register_blueprint(alert_bp, url_prefix="/api/alerts")

# Initialize background services
from services.background_service import start_background_tasks
start_background_tasks()
@app.route("/")
def home():
    return {"message": "Backend is running!"}

@app.route("/api/health", methods=["GET"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')