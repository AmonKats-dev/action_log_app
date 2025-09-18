from django.db.models.signals import post_save, pre_save, post_init
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in
from .models import Delegation, User
import logging

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Delegation)
def check_delegation_expiration(sender, instance, **kwargs):
    """Check if delegation has expired before saving"""
    if instance.expires_at and timezone.now() > instance.expires_at:
        instance.is_active = False
        logger.info(f"Delegation {instance.id} automatically deactivated due to expiration")

@receiver(post_init, sender=Delegation)
def check_delegation_expiration_on_access(sender, instance, **kwargs):
    """Check if delegation has expired when accessed"""
    if instance.expires_at and timezone.now() > instance.expires_at and instance.is_active:
        # Mark as inactive if expired
        instance.is_active = False
        # Use update to avoid triggering the pre_save signal again
        Delegation.objects.filter(id=instance.id).update(is_active=False)
        logger.info(f"Delegation {instance.id} automatically deactivated on access due to expiration")

@receiver(user_logged_in)
def check_user_delegations_on_login(sender, user, request, **kwargs):
    """Check for expired delegations when user logs in"""
    try:
        # Check and revoke expired delegations for the user's unit
        if user.department_unit:
            # Get all delegations in the user's unit and check for expired ones
            unit_delegations = Delegation.objects.filter(
                delegated_by__department_unit=user.department_unit,
                is_active=True
            )
            
            expired_count = 0
            for delegation in unit_delegations:
                if delegation.is_expired:
                    delegation.is_active = False
                    delegation.save()
                    expired_count += 1
                    logger.info(f"Delegation {delegation.id} automatically revoked on user {user.username} login")
            
            if expired_count > 0:
                logger.info(f"Revoked {expired_count} expired delegations on user {user.username} login")
                
    except Exception as e:
        logger.error(f"Error checking expired delegations on user {user.username} login: {e}")

def check_all_expired_delegations():
    """Utility function to check all expired delegations"""
    try:
        revoked_count = Delegation.revoke_expired_delegations()
        if revoked_count > 0:
            logger.info(f"Automatically revoked {revoked_count} expired delegations")
        return revoked_count
    except Exception as e:
        logger.error(f"Error checking expired delegations: {e}")
        return 0
