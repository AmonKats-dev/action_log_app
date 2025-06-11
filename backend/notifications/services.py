from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

logger = logging.getLogger(__name__)

class SMSNotificationService:
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = settings.TWILIO_PHONE_NUMBER
        print(f"Initializing SMS service with from_number: {self.from_number}")

    def send_notification(self, to_number, message):
        """
        Send an SMS notification to a user
        :param to_number: The recipient's phone number in E.164 format (e.g., +1234567890)
        :param message: The message to send
        :return: True if successful, False otherwise
        """
        try:
            # Format the phone numbers for SMS
            from_number = self.from_number.lstrip('+')
            to_number = to_number.lstrip('+')
            
            print(f"Attempting to send SMS from {from_number} to {to_number}")
            
            message = self.client.messages.create(
                body=message,
                from_=f"+{from_number}",
                to=f"+{to_number}"
            )
            print(f"SMS sent successfully: {message.sid}")
            return True
        except Exception as e:
            print(f"Error sending SMS: {str(e)}")
            logger.error(f"Error sending SMS: {str(e)}")
            return False

class WhatsAppNotificationService:
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = settings.TWILIO_PHONE_NUMBER
        print(f"Initializing WhatsApp service with from_number: {self.from_number}")

    def send_notification(self, to_number, message):
        try:
            # Format the phone numbers for WhatsApp
            # Ensure from_number has country code
            from_number = f"whatsapp:{self.from_number.lstrip('+')}"
            # Ensure to_number has country code and no plus sign
            to_number = f"whatsapp:{to_number.lstrip('+')}"
            
            print(f"Attempting to send WhatsApp message from {from_number} to {to_number}")
            
            message = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            print(f"WhatsApp message sent successfully: {message.sid}")
            return True
        except Exception as e:
            print(f"Error sending WhatsApp message: {str(e)}")
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False 