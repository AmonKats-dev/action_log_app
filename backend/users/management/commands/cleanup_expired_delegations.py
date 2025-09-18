#!/usr/bin/env python3
"""
Django management command to automatically clean up expired delegations.
This command should be run regularly (e.g., via cron) to ensure expired delegations
are properly deactivated and approval responsibilities are returned to Ag. C/PAP users.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import Delegation
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up expired delegations and ensure proper transition of approval responsibilities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each delegation',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS('Starting expired delegation cleanup...')
        )
        
        # Find all expired delegations that are still marked as active
        expired_delegations = Delegation.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        ).select_related('delegated_by', 'delegated_to')
        
        if not expired_delegations.exists():
            self.stdout.write(
                self.style.WARNING('No expired delegations found.')
            )
            return
        
        self.stdout.write(
            f'Found {expired_delegations.count()} expired delegations that need cleanup.'
        )
        
        if verbose:
            self.stdout.write('\nDetailed delegation information:')
            self.stdout.write('=' * 80)
        
        for delegation in expired_delegations:
            if verbose:
                self.stdout.write(f'\nDelegation ID: {delegation.id}')
                self.stdout.write(f'  From: {delegation.delegated_by.get_full_name()} ({delegation.delegated_by.designation})')
                self.stdout.write(f'  To: {delegation.delegated_to.get_full_name()} ({delegation.delegated_to.designation})')
                self.stdout.write(f'  Reason: {delegation.get_reason_display()}')
                self.stdout.write(f'  Created: {delegation.delegated_at}')
                self.stdout.write(f'  Expired: {delegation.expires_at}')
                self.stdout.write(f'  Time since expiry: {timezone.now() - delegation.expires_at}')
                
                # Show transition information
                if delegation.reason == 'leave':
                    self.stdout.write(f'  🏖️  LEAVE DELEGATION EXPIRED')
                    self.stdout.write(f'  📋 Approval responsibilities returning to: {delegation.delegated_by.get_full_name()}')
                    self.stdout.write(f'  📋 Ag. AC/PAP user losing responsibilities: {delegation.delegated_to.get_full_name()}')
                else:
                    self.stdout.write(f'  📋 REGULAR DELEGATION EXPIRED')
                    self.stdout.write(f'  📋 Responsibilities returning to: {delegation.delegated_by.get_full_name()}')
            
            if not dry_run:
                # Deactivate the expired delegation
                delegation.is_active = False
                delegation.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Deactivated expired delegation {delegation.id}')
                )
                
                # Log the transition for audit purposes
                if delegation.reason == 'leave':
                    logger.info(
                        f'Leave delegation {delegation.id} expired. '
                        f'Approval responsibilities returned from {delegation.delegated_to.get_full_name()} '
                        f'to {delegation.delegated_by.get_full_name()}. '
                        f'Expired at: {delegation.expires_at}'
                    )
                else:
                    logger.info(
                        f'Delegation {delegation.id} expired. '
                        f'Responsibilities returned from {delegation.delegated_to.get_full_name()} '
                        f'to {delegation.delegated_by.get_full_name()}. '
                        f'Expired at: {delegation.expires_at}'
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] Would deactivate delegation {delegation.id}')
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n[DRY RUN] No changes were made.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Successfully cleaned up {expired_delegations.count()} expired delegations.')
            )
            
            # Show summary of what happened
            leave_delegations = expired_delegations.filter(reason='leave')
            other_delegations = expired_delegations.exclude(reason='leave')
            
            if leave_delegations.exists():
                self.stdout.write(
                    self.style.SUCCESS(f'  🏖️  {leave_delegations.count()} leave delegations expired')
                    self.stdout.write(f'  📋 Approval responsibilities returned to Ag. C/PAP users')
                )
            
            if other_delegations.exists():
                self.stdout.write(
                    self.style.SUCCESS(f'  📋 {other_delegations.count()} other delegations expired')
                    self.stdout.write(f'  📋 Responsibilities returned to original users')
                )
        
        self.stdout.write(
            self.style.SUCCESS('\nExpired delegation cleanup completed successfully!')
        )
