#!/usr/bin/env python3
"""
Reset all user accounts and clean database for fresh start
"""

import os

import django

# Setup Django environment
os.environ.setdefault(
    "SCITEX_CLOUD_DJANGO_SETTINGS_MODULE", "config.settings.production"
)
django.setup()

from django.contrib.auth import get_user_model

from apps.infra.public_app.models import APIKey, Donation, Subscription
from apps.infra.workspace_app.models import (
    EmailVerification,
    Organization,
    Project,
    UserProfile,
)

User = get_user_model()


def safe_delete_model(model_class, model_name):
    """Safely delete all objects from a model, handling table not found errors"""
    try:
        count = model_class.objects.count()
        if count > 0:
            model_class.objects.all().delete()
            print(f"   ✓ {model_name} deleted ({count} items)")
        else:
            print(f"   ✓ {model_name} already empty")
        return True
    except Exception as e:
        print(f"   ⚠️  {model_name} deletion skipped: {str(e)}")
        return False


def reset_all_accounts():
    """Reset all user accounts and related data"""
    print("🔄 Resetting all user accounts...")

    # Count existing data safely
    try:
        user_count = User.objects.count()
        print(f"📊 Found {user_count} user accounts")
    except:
        user_count = 0
        print("📊 Unable to count users (table may not exist)")

    if user_count == 0:
        print("✅ No user accounts found. Database is already clean.")
        return True

    try:
        print("\n🗑️  Deleting user data...")

        # Delete in proper order to avoid foreign key constraints
        safe_delete_model(EmailVerification, "Email verifications")
        safe_delete_model(APIKey, "API keys")
        safe_delete_model(Subscription, "Subscriptions")
        safe_delete_model(Donation, "Donations")
        safe_delete_model(Project, "Projects")
        safe_delete_model(Organization, "Organizations")
        safe_delete_model(UserProfile, "User profiles")

        # Delete all users (including superusers)
        safe_delete_model(User, "Users")

        print("\n✅ All user accounts and related data have been reset!")
        print("🎯 The platform is now ready for fresh account creation.")
        return True

    except Exception as e:
        print(f"\n❌ Error resetting accounts: {str(e)}")
        return False


if __name__ == "__main__":
    print("=== SciTeX Account Reset ===")
    success = reset_all_accounts()

    if success:
        print("\n🚀 Account reset completed successfully!")
        print(
            "💡 You can now create new accounts with the fixed OTP verification system."
        )
    else:
        print("\nAccount reset failed.")
