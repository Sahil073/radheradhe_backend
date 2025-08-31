"""
Test cases for authentication system
"""

import pytest
import json
from app import app
from services.database_service import initialize_database

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    
    with app.test_client() as client:
        with app.app_context():
            initialize_database()
            yield client

def test_login_success(client):
    """Test successful login"""
    response = client.post('/api/auth/login', 
                          json={'email': 'admin@urjalink.com', 'password': 'admin123'})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data
    assert data['user']['role'] == 'admin'

def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post('/api/auth/login', 
                          json={'email': 'admin@urjalink.com', 'password': 'wrong'})
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'Invalid credentials' in data['message']

def test_login_missing_data(client):
    """Test login with missing data"""
    response = client.post('/api/auth/login', json={})
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'Email and password required' in data['message']

def test_protected_route_without_token(client):
    """Test accessing protected route without token"""
    response = client.get('/api/admin/overview')
    
    assert response.status_code == 401

def test_role_based_access(client):
    """Test role-based access control"""
    # Login as household user
    login_response = client.post('/api/auth/login', 
                                json={'email': 'house1@urjalink.com', 'password': 'house123'})
    
    token = json.loads(login_response.data)['access_token']
    
    # Try to access admin endpoint
    response = client.get('/api/admin/overview', 
                         headers={'Authorization': f'Bearer {token}'})
    
    assert response.status_code == 403