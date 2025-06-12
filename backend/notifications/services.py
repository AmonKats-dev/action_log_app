from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

logger = logging.getLogger(__name__)

class SMSNotificationService:
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = settings.TWILIO_PHONE_NUMBER
        logger.info("SMS notification service initialized")

    def send_notification(self, to_number, message):
        """
        Send SMS notification using Twilio.
        Handles rate limiting and other errors gracefully.
        """
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            logger.info(f"SMS sent successfully to {to_number}. SID: {message.sid}")
            return True
        except TwilioRestException as e:
            if e.code == 63038:  # Rate limit exceeded
                logger.warning(f"Twilio rate limit exceeded for number {to_number}. Message not sent.")
            else:
                logger.error(f"Error sending SMS to {to_number}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SMS to {to_number}: {str(e)}")
            return False

class WhatsAppNotificationService:
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = settings.TWILIO_PHONE_NUMBER
        logger.info("WhatsApp notification service initialized")

    def send_notification(self, to_number, message):
        try:
            # Format the phone numbers for WhatsApp
            # Ensure from_number has country code
            from_number = f"whatsapp:{self.from_number.lstrip('+')}"
            # Ensure to_number has country code and no plus sign
            to_number = f"whatsapp:{to_number.lstrip('+')}"
            
            logger.info(f"Sending WhatsApp message from {from_number} to {to_number}")
            
            message = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            logger.info(f"WhatsApp message sent successfully: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False 