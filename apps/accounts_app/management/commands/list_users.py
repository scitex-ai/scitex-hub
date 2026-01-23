#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django management command to list all users in the database.

Usage:
    python manage.py list_users
    python manage.py list_users --verbose
    python manage.py list_users --format json
    python manage.py list_users --staff-only
    python manage.py list_users --active-only

Or via Docker (production):
    docker exec scitex-cloud-prod-django-1 python manage.py list_users

Or via Docker (development):
    docker exec scitex-cloud-dev-django-1 python manage.py list_users
"""
import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "List all users in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed information for each user",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["table", "json", "csv"],
            default="table",
            help="Output format (default: table)",
        )
        parser.add_argument(
            "--staff-only",
            action="store_true",
            help="Show only staff users",
        )
        parser.add_argument(
            "--superuser-only",
            action="store_true",
            help="Show only superuser accounts",
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            help="Show only active users",
        )
        parser.add_argument(
            "--inactive-only",
            action="store_true",
            help="Show only inactive users",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        # Build queryset based on filters
        queryset = User.objects.all()

        if options["staff_only"]:
            queryset = queryset.filter(is_staff=True)

        if options["superuser_only"]:
            queryset = queryset.filter(is_superuser=True)

        if options["active_only"]:
            queryset = queryset.filter(is_active=True)

        if options["inactive_only"]:
            queryset = queryset.filter(is_active=False)

        queryset = queryset.order_by("date_joined")

        count = queryset.count()

        # Output header
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"Total users: {count}"))
        self.stdout.write("=" * 80)
        self.stdout.write("")

        if count == 0:
            self.stdout.write(self.style.WARNING("No users found."))
            return

        # Format output
        format_type = options["format"]

        if format_type == "json":
            self._output_json(queryset, options["verbose"])
        elif format_type == "csv":
            self._output_csv(queryset, options["verbose"])
        else:  # table
            self._output_table(queryset, options["verbose"])

    def _output_table(self, queryset, verbose):
        """Output as formatted table"""
        if verbose:
            # Detailed view
            for i, user in enumerate(queryset, 1):
                self.stdout.write(f"\n{i}. {user.username}")
                self.stdout.write(f"   Email:      {user.email}")
                self.stdout.write(f"   Active:     {user.is_active}")
                self.stdout.write(f"   Staff:      {user.is_staff}")
                self.stdout.write(f"   Superuser:  {user.is_superuser}")
                self.stdout.write(f"   Joined:     {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}")
                self.stdout.write(f"   Last login: {user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'}")
        else:
            # Compact table view
            header = f"{'Username':<20} {'Email':<35} {'Active':<8} {'Staff':<8} {'Super':<8} {'Joined':<12}"
            self.stdout.write(header)
            self.stdout.write("-" * len(header))

            for user in queryset:
                is_active = "Yes" if user.is_active else "No"
                is_staff = "Yes" if user.is_staff else "No"
                is_super = "Yes" if user.is_superuser else "No"
                joined = user.date_joined.strftime('%Y-%m-%d')

                row = f"{user.username:<20} {user.email:<35} {is_active:<8} {is_staff:<8} {is_super:<8} {joined:<12}"

                # Color code based on status
                if user.is_superuser:
                    self.stdout.write(self.style.ERROR(row))  # Red for superuser
                elif user.is_staff:
                    self.stdout.write(self.style.WARNING(row))  # Yellow for staff
                elif not user.is_active:
                    self.stdout.write(self.style.NOTICE(row))  # Gray for inactive
                else:
                    self.stdout.write(row)

    def _output_json(self, queryset, verbose):
        """Output as JSON"""
        users_data = []
        for user in queryset:
            user_dict = {
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined.isoformat(),
            }

            if verbose:
                user_dict.update({
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                })

            users_data.append(user_dict)

        self.stdout.write(json.dumps(users_data, indent=2))

    def _output_csv(self, queryset, verbose):
        """Output as CSV"""
        if verbose:
            header = "username,email,is_active,is_staff,is_superuser,date_joined,last_login,first_name,last_name"
        else:
            header = "username,email,is_active,is_staff,is_superuser,date_joined"

        self.stdout.write(header)

        for user in queryset:
            if verbose:
                row = f"{user.username},{user.email},{user.is_active},{user.is_staff},{user.is_superuser},{user.date_joined.isoformat()},{user.last_login.isoformat() if user.last_login else ''},{user.first_name},{user.last_name}"
            else:
                row = f"{user.username},{user.email},{user.is_active},{user.is_staff},{user.is_superuser},{user.date_joined.isoformat()}"

            self.stdout.write(row)
