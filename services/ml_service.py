"""
Enhanced Machine Learning service with multiple models
Includes battery prediction, demand forecasting, and anomaly detection
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import pickle
import os
import logging

logger = logging.getLogger(__name__)

class EnergyMLService:
    def __init__(self):
        self.battery_model = LinearRegression()
        self.demand_model = LinearRegression()
        self.anomaly_detector = IsolationForest(contamination=0.1)
        self.scaler = StandardScaler()
        self.models_trained = False
        
    def train_models(self, historical_data):
        """Train ML models with historical data"""
        try:
            if not historical_data:
                logger.warning("No historical data available for training")
                return False
                
            df = pd.DataFrame(historical_data)
            
            # Prepare features for battery prediction
            battery_features = ['input_power', 'output_power', 'solar_generation']
            if all(col in df.columns for col in battery_features):
                X_battery = df[battery_features].fillna(0)
                y_battery = df['battery_percentage'].fillna(50)
                
                self.battery_model.fit(X_battery, y_battery)
                
            # Prepare features for demand forecasting
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
            
            demand_features = ['hour', 'day_of_week', 'solar_generation']
            if all(col in df.columns for col in demand_features):
                X_demand = df[demand_features].fillna(0)
                y_demand = df['output_power'].fillna(0)
                
                self.demand_model.fit(X_demand, y_demand)
                
            # Train anomaly detector
            anomaly_features = ['input_power', 'output_power', 'battery_voltage']
            if all(col in df.columns for col in anomaly_features):
                X_anomaly = df[anomaly_features].fillna(0)
                X_anomaly_scaled = self.scaler.fit_transform(X_anomaly)
                self.anomaly_detector.fit(X_anomaly_scaled)
                
            self.models_trained = True
            self._save_models()
            logger.info("ML models trained successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
            return False
    
    def predict_battery_sustain(self, current_data):
        """
        Predict battery sustain time using multiple factors
        """
        try:
            battery_voltage = current_data.get("batteryVoltage", 12)
            input_power = current_data.get("inputPower", 0)
            output_power = current_data.get("outputPower", 0)
            solar_generation = current_data.get("solarGeneration", 0)
            
            # Simple physics-based calculation as fallback
            if output_power <= 0:
                return float("inf")
                
            # Estimate battery capacity (simplified)
            battery_capacity_wh = (battery_voltage - 10.5) / (12.6 - 10.5) * 100  # Rough %
            net_consumption = output_power - input_power - solar_generation
            
            if net_consumption <= 0:
                return float("inf")  # Battery is charging or stable
                
            hours = (battery_capacity_wh * 0.8) / net_consumption  # 80% usable capacity
            
            # Use ML model if trained
            if self.models_trained:
                try:
                    features = np.array([[input_power, output_power, solar_generation]])
                    ml_prediction = self.battery_model.predict(features)[0]
                    # Combine physics and ML prediction
                    hours = (hours + ml_prediction) / 2
                except Exception as e:
                    logger.warning(f"ML prediction failed, using physics model: {e}")
                    
            return max(0, round(hours, 2))
            
        except Exception as e:
            logger.error(f"Error predicting battery sustain: {e}")
            return 0
    
    def predict_demand(self, hour, day_of_week, solar_forecast):
        """Predict energy demand for given time"""
        try:
            if not self.models_trained:
                # Simple heuristic based on time of day
                if 6 <= hour <= 18:  # Daytime
                    return 50 + (solar_forecast * 0.3)
                else:  # Nighttime
                    return 30
                    
            features = np.array([[hour, day_of_week, solar_forecast]])
            prediction = self.demand_model.predict(features)[0]
            return max(0, prediction)
            
        except Exception as e:
            logger.error(f"Error predicting demand: {e}")
            return 40  # Default demand
    
    def detect_anomaly(self, current_data):
        """Detect anomalies in energy data"""
        try:
            input_power = current_data.get("inputPower", 0)
            output_power = current_data.get("outputPower", 0)
            battery_voltage = current_data.get("batteryVoltage", 12)
            
            # Rule-based anomaly detection
            anomalies = []
            
            # Check for impossible values
            if battery_voltage < 9 or battery_voltage > 15:
                anomalies.append("Battery voltage out of range")
                
            if output_power > input_power * 2:
                anomalies.append("Output power significantly exceeds input")
                
            if input_power < 0 or output_power < 0:
                anomalies.append("Negative power values detected")
                
            # ML-based anomaly detection if trained
            if self.models_trained:
                try:
                    features = np.array([[input_power, output_power, battery_voltage]])
                    features_scaled = self.scaler.transform(features)
                    is_anomaly = self.anomaly_detector.predict(features_scaled)[0] == -1
                    
                    if is_anomaly:
                        anomalies.append("ML model detected anomaly")
                        
                except Exception as e:
                    logger.warning(f"ML anomaly detection failed: {e}")
            
            return {
                "hasAnomaly": len(anomalies) > 0,
                "anomalies": anomalies,
                "severity": "HIGH" if len(anomalies) > 1 else "MEDIUM" if anomalies else "LOW"
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomaly: {e}")
            return {"hasAnomaly": False, "anomalies": [], "severity": "LOW"}
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            models_dir = "models"
            os.makedirs(models_dir, exist_ok=True)
            
            with open(f"{models_dir}/battery_model.pkl", "wb") as f:
                pickle.dump(self.battery_model, f)
                
            with open(f"{models_dir}/demand_model.pkl", "wb") as f:
                pickle.dump(self.demand_model, f)
                
            with open(f"{models_dir}/anomaly_detector.pkl", "wb") as f:
                pickle.dump(self.anomaly_detector, f)
                
            with open(f"{models_dir}/scaler.pkl", "wb") as f:
                pickle.dump(self.scaler, f)
                
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def load_models(self):
        """Load trained models from disk"""
        try:
            models_dir = "models"
            
            if os.path.exists(f"{models_dir}/battery_model.pkl"):
                with open(f"{models_dir}/battery_model.pkl", "rb") as f:
                    self.battery_model = pickle.load(f)
                    
                with open(f"{models_dir}/demand_model.pkl", "rb") as f:
                    self.demand_model = pickle.load(f)
                    
                with open(f"{models_dir}/anomaly_detector.pkl", "rb") as f:
                    self.anomaly_detector = pickle.load(f)
                    
                with open(f"{models_dir}/scaler.pkl", "rb") as f:
                    self.scaler = pickle.load(f)
                    
                self.models_trained = True
                logger.info("ML models loaded successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            
        return False

# Global ML service instance
ml_service = EnergyMLService()
ml_service.load_models()

# Convenience functions for backward compatibility
def predict_battery_sustain(battery_voltage, output_power):
    """Legacy function - use ml_service.predict_battery_sustain instead"""
    data = {
        "batteryVoltage": battery_voltage,
        "outputPower": output_power,
        "inputPower": 0,
        "solarGeneration": 0
    }
    return ml_service.predict_battery_sustain(data)

def detect_anomaly(input_power, output_power):
    """Legacy function - use ml_service.detect_anomaly instead"""
    data = {
        "inputPower": input_power,
        "outputPower": output_power,
        "batteryVoltage": 12
    }
    result = ml_service.detect_anomaly(data)
    return result["hasAnomaly"]