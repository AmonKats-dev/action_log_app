from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import Delegation
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Automatically revoke expired delegations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be revoked without actually revoking',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all expired delegations
        expired_delegations = Delegation.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )
        
        if not expired_delegations.exists():
            self.stdout.write(
                self.style.SUCCESS('No expired delegations found.')
            )
            return
        
        self.stdout.write(
            f'Found {expired_delegations.count()} expired delegations:'
        )
        
        for delegation in expired_delegations:
            self.stdout.write(
                f'  - {delegation.delegated_by.get_full_name()} → '
                f'{delegation.delegated_to.get_full_name()} '
                f'(expired: {delegation.expires_at})'
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    'DRY RUN: No delegations were actually revoked. '
                    'Use without --dry-run to execute.'
                )
            )
            return
        
        # Revoke expired delegations
        count = expired_delegations.count()
        expired_delegations.update(is_active=False)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully revoked {count} expired delegations.'
            )
        )
        
        # Log the action
        logger.info(f'Revoked {count} expired delegations via management command')
