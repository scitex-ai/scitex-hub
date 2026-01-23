#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django management command to initialize test user for development.

Usage:
    python manage.py init_test_user

Or via Docker:
    docker exec scitex-cloud-dev-django-1 python manage.py init_test_user
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Initialize test user for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default="test-user",
            help="Username for the test user (default: test-user)",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="Password123!",
            help="Password for the test user (default: Password123!)",
        )
        parser.add_argument(
            "--email",
            type=str,
            default="test@example.com",
            help="Email for the test user (default: test@example.com)",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        password = options["password"]
        email = options["email"]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )

        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Test user created: {username}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Test user updated: {username}")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCredentials:\n  Username: {username}\n  Password: {password}\n  Email: {email}"
            )
        )
