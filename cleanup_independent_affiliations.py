#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to remove 'Independent' organization enrollments for individuals
who also have 'Interledger Foundation' enrollments.
"""

import sys
import os
import django
from datetime import datetime

# Add the sortinghat path to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src/grimoirelab-sortinghat'))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sortinghat.config.settings')
django.setup()

from sortinghat.core.models import Individual, Enrollment, Group


def cleanup_independent_affiliations(dry_run=True):
    """
    Remove 'Independent' enrollments for individuals who also have
    'Interledger Foundation' enrollments.

    Args:
        dry_run: If True, only print what would be done without making changes
    """
    try:
        # Get the organizations
        independent_org = Group.objects.get(name='Independent')
        interledger_org = Group.objects.get(name='Interledger Foundation')

        print(f"Found organizations:")
        print(f"  - Independent (ID: {independent_org.id})")
        print(f"  - Interledger Foundation (ID: {interledger_org.id})")
        print()

    except Group.DoesNotExist as e:
        print(f"Error: Organization not found - {e}")
        return

    # Find all individuals enrolled in Interledger Foundation
    interledger_individuals = Individual.objects.filter(
        enrollments__group=interledger_org
    ).distinct()

    print(f"Found {interledger_individuals.count()} individuals enrolled in Interledger Foundation")
    print()

    # Track statistics
    individuals_affected = 0
    enrollments_removed = 0

    # For each individual with Interledger Foundation enrollment
    for individual in interledger_individuals:
        # Check if they also have Independent enrollment
        independent_enrollments = Enrollment.objects.filter(
            individual=individual,
            group=independent_org
        )

        if independent_enrollments.exists():
            individuals_affected += 1
            count = independent_enrollments.count()
            enrollments_removed += count

            print(f"Individual: {individual.mk}")
            print(f"  Profile: {individual.profile.name if hasattr(individual, 'profile') and individual.profile.name else 'N/A'}")
            print(f"  Email: {individual.profile.email if hasattr(individual, 'profile') and individual.profile.email else 'N/A'}")
            print(f"  Independent enrollments to remove: {count}")

            for enrollment in independent_enrollments:
                print(f"    - Period: {enrollment.start} to {enrollment.end}")

            if not dry_run:
                independent_enrollments.delete()
                print(f"  ✓ Removed {count} Independent enrollment(s)")
            else:
                print(f"  [DRY RUN] Would remove {count} Independent enrollment(s)")

            print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Individuals affected: {individuals_affected}")
    print(f"Enrollments removed: {enrollments_removed}")

    if dry_run:
        print("\nThis was a DRY RUN - no changes were made.")
        print("Run with --execute to apply changes.")
    else:
        print("\nChanges have been applied successfully!")


if __name__ == '__main__':
    # Check for --execute flag
    dry_run = '--execute' not in sys.argv

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 60)
        print()
    else:
        print("=" * 60)
        print("EXECUTE MODE - Changes will be applied")
        print("=" * 60)
        print()
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
        print()

    cleanup_independent_affiliations(dry_run=dry_run)
