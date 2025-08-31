# Smart Microgrid Energy Management Backend

A robust Flask-based backend system for managing smart microgrid energy distribution with ML-powered optimization, real-time monitoring, and comprehensive security.

## Features

### 🔐 Authentication & Security
- JWT-based authentication with role-based access control
- Admin and Household user roles with different permissions
- Secure API endpoints with rate limiting
- Comprehensive audit logging

### ⚡ Energy Management
- Real-time sensor data processing from Firebase
- 4-zone relay control system with priority levels:
  - **Critical**: Hospital, Emergency lights (always ON unless battery < 10%)
  - **Semi-critical**: Street lights, Fans
  - **Non-critical**: TV, Entertainment
  - **Deferrable**: Water pumps, Washing machines

### 🤖 ML & Optimization
- Battery sustain time prediction using Linear Regression
- Demand forecasting with time-series analysis
- Anomaly detection using Isolation Forest
- Advanced optimization algorithms:
  - Greedy algorithm for immediate decisions
  - Dynamic programming for scheduling
  - Load balancing to prevent overload

### 📱 Communication & Alerts
- Multi-channel notifications (SMS, Email, Firebase Push)
- Emergency alert system with escalation
- Low battery warnings
- Admin-to-household messaging

### 🔄 Background Services
- Continuous system monitoring
- Automatic optimization every 5 minutes
- Model retraining with new data
- Watchdog service for reliability

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - User logout
- `GET /api/auth/profile` - Get user profile

### Admin APIs
- `POST /api/admin/control` - Control any zone (override)
- `GET /api/admin/overview` - System overview
- `POST /api/admin/optimize` - Force optimization
- `GET /api/admin/logs` - Audit logs
- `POST /api/admin/message` - Send message to household

### Energy APIs
- `GET /api/energy/status` - Current energy status
- `POST /api/energy/updateVoltage` - ESP32 voltage updates
- `GET /api/energy/history` - Historical data
- `POST /api/energy/optimize` - Manual optimization
- `GET /api/energy/predictions` - ML predictions

### Household APIs
- `GET /api/household/status` - Household energy data
- `POST /api/household/control` - Limited zone control
- `GET /api/household/notifications` - Get notifications
- `POST /api/household/notifications/read` - Mark as read

### Scenario APIs
- `POST /api/scenario/apply` - Apply optimization
- `GET /api/scenario/schedule` - Get optimization schedule
- `POST /api/scenario/simulate` - Simulate optimization

### Alert APIs
- `GET /api/alerts/history` - Alert history
- `POST /api/alerts/send` - Send custom alert
- `POST /api/alerts/emergency` - Trigger emergency alert

## Setup Instructions

### 1. Environment Variables
Create a `.env` file with:

```env
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
FIREBASE_DB_URL=https://your-project.firebaseio.com/
FIREBASE_CREDENTIALS_PATH=firebase-key.json
POSTGRES_URL=postgresql://user:password@localhost:5432/microgrid
REDIS_URL=redis://localhost:6379/0
TWILIO_SID=your-twilio-sid
TWILIO_AUTH=your-twilio-auth-token
TWILIO_PHONE=your-twilio-phone
ADMIN_PHONE=+1234567890
ADMIN_EMAIL=admin@urjalink.com
```

### 2. Firebase Setup
1. Create a Firebase project
2. Enable Realtime Database
3. Download service account key as `firebase-key.json`
4. Set up database structure:

```json
{
  "sensors": {
    "Zone1": {
      "batteryVoltage": 12.5,
      "inputPower": 45.2,
      "outputPower": 38.7,
      "solarGeneration": 25.3,
      "batteryPercentage": 85.2,
      "relayState": true,
      "timestamp": "2025-01-27T10:30:00Z"
    }
  },
  "commands": {
    "Zone1": {
      "command": "ON",
      "timestamp": 1706356200
    }
  }
}
```

### 3. Database Setup
```bash
# Install PostgreSQL and Redis
sudo apt-get install postgresql redis-server

# Create database
sudo -u postgres createdb microgrid

# Run initialization
python -c "from services.database_service import initialize_database; initialize_database()"
```

### 4. Run the Application

#### Development
```bash
pip install -r requirements.txt
python app.py
```

#### Production with Docker
```bash
docker-compose up -d
```

#### With Celery (Background Tasks)
```bash
# Terminal 1: Start Flask app
python app.py

# Terminal 2: Start Celery worker
celery -A celery_app.celery worker --loglevel=info

# Terminal 3: Start Celery beat (scheduler)
celery -A celery_app.celery beat --loglevel=info
```

## System Architecture

### Data Flow
1. **ESP32 devices** → Send sensor data → **Firebase Realtime DB**
2. **Backend** → Fetches data → **Processes with ML models**
3. **Optimization Engine** → Makes decisions → **Sends commands to Firebase**
4. **ESP32 devices** → Read commands → **Control physical relays**

### Security Layers
- JWT authentication with role-based access
- Input validation and sanitization
- Rate limiting on sensitive endpoints
- Comprehensive audit logging
- TLS/SSL encryption (configure reverse proxy)

### Monitoring & Alerts
- Real-time system monitoring
- Battery level alerts (20%, 10%, 5% thresholds)
- Anomaly detection and alerts
- Emergency escalation procedures
- Daily energy reports

## Zone Priority System

1. **Critical Zones** (Priority 1)
   - Always ON unless battery < 10%
   - Hospital equipment, emergency lighting
   - Cannot be turned OFF by households

2. **Semi-Critical Zones** (Priority 2)
   - Street lights, essential fans
   - Auto-controlled based on time and battery
   - Limited household control

3. **Non-Critical Zones** (Priority 3)
   - Entertainment, non-essential lighting
   - Household can control when battery > 20%

4. **Deferrable Zones** (Priority 4)
   - Water pumps, washing machines
   - Scheduled during optimal times
   - First to be turned OFF during shortages

## ML Models

### Battery Prediction Model
- **Input**: Current power, solar generation, historical patterns
- **Output**: Hours until battery depletion
- **Algorithm**: Linear Regression with feature engineering

### Demand Forecasting
- **Input**: Time of day, day of week, weather data
- **Output**: Predicted power consumption
- **Algorithm**: Time-series regression

### Anomaly Detection
- **Input**: Power consumption patterns
- **Output**: Anomaly score and classification
- **Algorithm**: Isolation Forest

## Optimization Algorithms

### Greedy Algorithm
- Immediate decisions based on current state
- Prioritizes critical zones
- Considers efficiency and battery level

### Dynamic Programming
- Long-term scheduling optimization
- Maximizes overall system uptime
- Balances comfort vs. energy conservation

### Load Balancing
- Prevents system overload
- Distributes power based on priority
- Maintains 90% safety margin

## Emergency Procedures

### Battery Emergency (< 10%)
1. Immediately shutdown non-critical zones
2. Send emergency alerts to admin
3. Maintain only critical zones
4. Log all actions for audit

### Critical Zone Failure
1. Attempt automatic restart
2. Send immediate emergency alert
3. Escalate if restart fails
4. Notify authorities if hospital affected

### Communication Failure
1. Retry commands with exponential backoff
2. Switch to backup communication channels
3. Log failures for investigation
4. Alert admin of persistent issues

## Deployment

### Production Checklist
- [ ] Configure environment variables
- [ ] Set up SSL/TLS certificates
- [ ] Configure reverse proxy (Nginx)
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Test emergency procedures
- [ ] Configure firewall rules

### Scaling Considerations
- Use Gunicorn with multiple workers
- Implement Redis clustering for high availability
- Set up PostgreSQL read replicas
- Use load balancer for multiple backend instances
- Implement circuit breakers for external services

## Monitoring & Maintenance

### Health Checks
- Database connectivity
- Firebase connectivity
- Redis availability
- Celery worker status
- Model performance metrics

### Regular Maintenance
- Model retraining (weekly)
- Database cleanup (monthly)
- Log rotation (daily)
- Security updates (as needed)
- Performance optimization (quarterly)

## Troubleshooting

### Common Issues
1. **Firebase connection errors**: Check credentials and network
2. **Database connection issues**: Verify PostgreSQL service
3. **Celery tasks not running**: Check Redis connection
4. **SMS not sending**: Verify Twilio credentials
5. **High memory usage**: Check for data leaks in ML models

### Debug Mode
Set `FLASK_ENV=development` for detailed error messages and auto-reload.

### Logs Location
- Application logs: `app.log`
- Audit logs: Database `audit_logs` table
- Celery logs: Console output
- System logs: `/var/log/` (production)