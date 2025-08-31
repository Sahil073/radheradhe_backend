"""
Enhanced notification system with multiple channels
Supports SMS, Email, and Firebase push notifications
"""

import logging
from twilio.rest import Client
from config import Config
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from services.firebase_service import db

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.twilio_client = None
        if Config.TWILIO_SID and Config.TWILIO_AUTH:
            self.twilio_client = Client(Config.TWILIO_SID, Config.TWILIO_AUTH)
    
    def send_sms(self, to, message, priority="NORMAL"):
        """Send SMS notification using Twilio"""
        if not self.twilio_client:
            logger.error("Twilio not configured")
            return False
            
        try:
            message_obj = self.twilio_client.messages.create(
                to=to,
                from_=Config.TWILIO_PHONE,
                body=message
            )
            
            logger.info(f"SMS sent successfully: {message_obj.sid}")
            self._log_notification("SMS", to, message, "SENT", priority)
            return True
            
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            self._log_notification("SMS", to, message, "FAILED", priority)
            return False
    
    def send_email(self, to, subject, message, priority="NORMAL"):
        """Send email notification"""
        try:
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            sender_email = Config.ADMIN_EMAIL
            sender_password = Config.EMAIL_PASSWORD  # store in config
            
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {to}")
            self._log_notification("EMAIL", to, f"{subject}: {message}", "SENT", priority)
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            self._log_notification("EMAIL", to, f"{subject}: {message}", "FAILED", priority)
            return False
    
    def send_firebase_notification(self, user_id, title, body, data=None):
        """Send Firebase push notification"""
        try:
            notification_data = {
                "title": title,
                "body": body,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data or {},
                "read": False
            }
            
            ref = db.reference(f"notifications/{user_id}")
            ref.push(notification_data)
            
            logger.info(f"Firebase notification sent to user {user_id}")
            self._log_notification("FIREBASE", user_id, f"{title}: {body}", "SENT")
            return True
            
        except Exception as e:
            logger.error(f"Firebase notification failed: {e}")
            self._log_notification("FIREBASE", user_id, f"{title}: {body}", "FAILED")
            return False
    
    def send_emergency_alert(self, alert_type, details, affected_zones=None):
        """Send emergency alert through all channels"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🚨 EMERGENCY ALERT 🚨\n"
        message += f"Type: {alert_type}\n"
        message += f"Time: {timestamp}\n"
        message += f"Details: {details}\n"
        
        if affected_zones:
            message += f"Affected Zones: {', '.join(affected_zones)}\n"
        
        message += "Immediate action required!"
        
        results = {}
        
        if Config.ADMIN_PHONE:
            results["sms"] = self.send_sms(Config.ADMIN_PHONE, message, "EMERGENCY")
        
        if Config.ADMIN_EMAIL:
            results["email"] = self.send_email(
                Config.ADMIN_EMAIL, 
                f"EMERGENCY: {alert_type}", 
                message, 
                "EMERGENCY"
            )
        
        results["firebase"] = self.send_firebase_notification(
            "admin", 
            f"Emergency: {alert_type}", 
            details,
            {"type": "emergency", "zones": affected_zones}
        )
        
        return results
    
    def send_low_battery_alert(self, battery_level, affected_zones):
        """Send low battery alert"""
        message = f"⚠️ Low Battery Alert\n"
        message += f"Battery Level: {battery_level:.1f}%\n"
        message += f"Affected Zones: {', '.join(affected_zones)}\n"
        message += f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        
        results = {}
        
        if Config.ADMIN_PHONE:
            results["sms"] = self.send_sms(Config.ADMIN_PHONE, message, "HIGH")
        
        results["firebase"] = self.send_firebase_notification(
            "admin",
            "Low Battery Warning",
            f"Battery at {battery_level:.1f}%",
            {"type": "low_battery", "level": battery_level}
        )
        
        return results
    
    def send_admin_message_to_household(self, household_id, message):
        """Send message from admin to specific household"""
        try:
            notification_data = {
                "title": "Message from Admin",
                "body": message,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "admin_message",
                "read": False
            }
            
            ref = db.reference(f"notifications/household_{household_id}")
            ref.push(notification_data)
            
            logger.info(f"Admin message sent to household {household_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send admin message: {e}")
            return False
    
    def _log_notification(self, channel, recipient, message, status, priority="NORMAL"):
        """Log notification to Firebase (instead of SQL DB)"""
        try:
            log_data = {
                "channel": channel,
                "recipient": recipient,
                "message": message,
                "status": status,
                "priority": priority,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            ref = db.reference("notification_logs")
            ref.push(log_data)
            
        except Exception as e:
            logger.error(f"Error logging notification: {e}")

# Global notification service instance
notification_service = NotificationService()
