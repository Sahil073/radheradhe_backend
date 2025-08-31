"""
Database service for PostgreSQL operations
Handles user management, logging, and data caching
"""

import psycopg2
import redis
import json
from datetime import datetime, timedelta
from config import Config
from werkzeug.security import generate_password_hash

# Database connection
def get_db_connection():
    """Get PostgreSQL connection"""
    try:
        conn = psycopg2.connect(Config.POSTGRES_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Redis connection
def get_redis_connection():
    """Get Redis connection for caching"""
    try:
        return redis.from_url(Config.REDIS_URL)
    except Exception as e:
        print(f"Redis connection error: {e}")
        return None

def initialize_database():
    """Initialize database tables"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                household_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id VARCHAR(100),
                action TEXT NOT NULL,
                zone VARCHAR(50),
                extra_data JSONB,
                ip_address INET
            )
        """)
        
        # Energy data cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS energy_data (
                id SERIAL PRIMARY KEY,
                zone VARCHAR(50) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                battery_voltage FLOAT,
                input_power FLOAT,
                output_power FLOAT,
                solar_generation FLOAT,
                battery_percentage FLOAT,
                relay_state BOOLEAN
            )
        """)
        
        # Optimization decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_decisions (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                decision_data JSONB NOT NULL,
                battery_level FLOAT,
                predicted_sustain_hours FLOAT,
                triggered_by VARCHAR(100)
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                alert_type VARCHAR(100) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                message TEXT NOT NULL,
                recipient VARCHAR(255),
                status VARCHAR(20) DEFAULT 'sent',
                zone VARCHAR(50)
            )
        """)
        
        # Insert default admin user
        cursor.execute("""
            INSERT INTO users (email, password_hash, role) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (email) DO NOTHING
        """, ("admin@urjalink.com", generate_password_hash("admin123"), "admin"))
        
        # Insert default household user
        cursor.execute("""
            INSERT INTO users (email, password_hash, role, household_id) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (email) DO NOTHING
        """, ("house1@urjalink.com", generate_password_hash("house123"), "household", "H001"))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def get_user_by_email(email):
    """Get user by email"""
    conn = get_db_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, password_hash, role, household_id, is_active 
            FROM users WHERE email = %s AND is_active = TRUE
        """, (email,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            return {
                "id": str(row[0]),
                "email": row[1],
                "password_hash": row[2],
                "role": row[3],
                "householdId": row[4],
                "is_active": row[5]
            }
        return None
        
    except Exception as e:
        print(f"Error fetching user: {e}")
        if conn:
            conn.close()
        return None

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, role, household_id, is_active 
            FROM users WHERE id = %s AND is_active = TRUE
        """, (user_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            return {
                "id": str(row[0]),
                "email": row[1],
                "role": row[2],
                "householdId": row[3],
                "is_active": row[4]
            }
        return None
        
    except Exception as e:
        print(f"Error fetching user by ID: {e}")
        if conn:
            conn.close()
        return None

def log_to_database(log_entry):
    """Log entry to database"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, zone, extra_data, ip_address)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            log_entry.get("user_id"),
            log_entry.get("action"),
            log_entry.get("zone"),
            json.dumps(log_entry.get("extra_data", {})),
            log_entry.get("extra_data", {}).get("ip")
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error logging to database: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def cache_energy_data(zone, data):
    """Cache energy data in Redis"""
    redis_client = get_redis_connection()
    if not redis_client:
        return False
        
    try:
        # Cache for 5 minutes
        redis_client.setex(
            f"energy_data:{zone}",
            300,
            json.dumps(data)
        )
        return True
    except Exception as e:
        print(f"Error caching energy data: {e}")
        return False

def get_cached_energy_data(zone):
    """Get cached energy data from Redis"""
    redis_client = get_redis_connection()
    if not redis_client:
        return None
        
    try:
        data = redis_client.get(f"energy_data:{zone}")
        return json.loads(data) if data else None
    except Exception as e:
        print(f"Error getting cached data: {e}")
        return None

def store_energy_data(zone, data):
    """Store energy data in PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO energy_data 
            (zone, battery_voltage, input_power, output_power, solar_generation, 
             battery_percentage, relay_state)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            zone,
            data.get("batteryVoltage"),
            data.get("inputPower"),
            data.get("outputPower"),
            data.get("solarGeneration"),
            data.get("batteryPercentage"),
            data.get("relayState")
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error storing energy data: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def get_energy_history(zone, hours=24):
    """Get energy history for a zone"""
    conn = get_db_connection()
    if not conn:
        return []
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, battery_voltage, input_power, output_power, 
                   solar_generation, battery_percentage, relay_state
            FROM energy_data 
            WHERE zone = %s AND timestamp >= %s
            ORDER BY timestamp DESC
        """, (zone, datetime.utcnow() - timedelta(hours=hours)))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [{
            "timestamp": row[0].isoformat(),
            "batteryVoltage": row[1],
            "inputPower": row[2],
            "outputPower": row[3],
            "solarGeneration": row[4],
            "batteryPercentage": row[5],
            "relayState": row[6]
        } for row in rows]
        
    except Exception as e:
        print(f"Error getting energy history: {e}")
        if conn:
            conn.close()
        return []