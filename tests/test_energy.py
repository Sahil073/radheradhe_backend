"""
Test cases for energy management system
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from app import app
from services.ml_service import ml_service

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def admin_token(client):
    """Get admin token for testing"""
    response = client.post('/api/auth/login', 
                          json={'email': 'admin@urjalink.com', 'password': 'admin123'})
    return json.loads(response.data)['access_token']

@patch('services.firebase_service.get_sensor_data')
def test_energy_status(mock_get_sensor_data, client):
    """Test energy status endpoint"""
    mock_get_sensor_data.return_value = {
        "Zone1": {
            "batteryVoltage": 12.5,
            "inputPower": 45.2,
            "outputPower": 38.7,
            "solarGeneration": 25.3,
            "batteryPercentage": 85.2,
            "relayState": True
        }
    }
    
    response = client.get('/api/energy/status')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'system_metrics' in data
    assert 'zones' in data

def test_battery_sustain_prediction():
    """Test battery sustain prediction"""
    test_data = {
        "batteryVoltage": 12.5,
        "inputPower": 45.2,
        "outputPower": 38.7,
        "solarGeneration": 25.3
    }
    
    sustain_hours = ml_service.predict_battery_sustain(test_data)
    
    assert isinstance(sustain_hours, (int, float))
    assert sustain_hours >= 0

def test_anomaly_detection():
    """Test anomaly detection"""
    normal_data = {
        "inputPower": 45.2,
        "outputPower": 38.7,
        "batteryVoltage": 12.5
    }
    
    anomaly_result = ml_service.detect_anomaly(normal_data)
    
    assert isinstance(anomaly_result, dict)
    assert 'hasAnomaly' in anomaly_result
    assert 'severity' in anomaly_result

@patch('services.firebase_service.set_command')
def test_admin_zone_control(mock_set_command, client, admin_token):
    """Test admin zone control"""
    mock_set_command.return_value = True
    
    response = client.post('/api/admin/control',
                          json={'zone': 'Zone1', 'action': 'ON'},
                          headers={'Authorization': f'Bearer {admin_token}'})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'Zone Zone1 set to ON' in data['message']

def test_invalid_zone_control(client, admin_token):
    """Test control of invalid zone"""
    response = client.post('/api/admin/control',
                          json={'zone': 'InvalidZone', 'action': 'ON'},
                          headers={'Authorization': f'Bearer {admin_token}'})
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'Invalid zone' in data['message']