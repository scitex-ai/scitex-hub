from django.core.management.base import BaseCommand
from apps.infra.public_app.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Create subscription plans based on premium strategy"

    def handle(self, *args, **options):
        # Define the plans from the premium strategy
        plans_data = [
            {
                "name": "Free",
                "plan_type": "free",
                "price_monthly": 0.00,
                "price_yearly": 0.00,
                "max_projects": 1,
                "storage_gb": 1,  # 500MB converted to GB for simplicity
                "cpu_cores": 1,
                "gpu_vram_gb": 1,
                "has_watermark": True,
                "requires_citation": True,
                "requires_archive": True,
                "has_priority_support": False,
                "has_custom_integrations": False,
                "has_team_collaboration": False,
                "is_featured": False,
                "is_active": True,
                "display_order": 1,
            },
            {
                "name": "Standard",
                "plan_type": "premium_a",
                "price_monthly": 29.00,
                "price_yearly": 290.00,  # 2 months free
                "max_projects": 5,
                "storage_gb": 5,
                "cpu_cores": 2,
                "gpu_vram_gb": 4,
                "has_watermark": False,
                "requires_citation": True,
                "requires_archive": False,
                "has_priority_support": True,
                "has_custom_integrations": False,
                "has_team_collaboration": True,
                "is_featured": False,
                "is_active": True,
                "display_order": 2,
            },
            {
                "name": "Professional",
                "plan_type": "premium_b",
                "price_monthly": 99.00,
                "price_yearly": 990.00,  # 2 months free
                "max_projects": 20,
                "storage_gb": 25,
                "cpu_cores": 4,
                "gpu_vram_gb": 8,
                "has_watermark": False,
                "requires_citation": False,
                "requires_archive": False,
                "has_priority_support": True,
                "has_custom_integrations": True,
                "has_team_collaboration": True,
                "is_featured": True,
                "is_active": True,
                "display_order": 3,
            },
            {
                "name": "Researcher Plus",
                "plan_type": "enterprise",
                "price_monthly": 199.00,
                "price_yearly": 1990.00,  # 2 months free
                "max_projects": 100,
                "storage_gb": 100,
                "cpu_cores": 8,
                "gpu_vram_gb": 16,
                "has_watermark": False,
                "requires_citation": False,
                "requires_archive": False,
                "has_priority_support": True,
                "has_custom_integrations": True,
                "has_team_collaboration": True,
                "is_featured": False,
                "is_active": True,
                "display_order": 4,
            },
            {
                "name": "University Enterprise",
                "plan_type": "custom",
                "price_monthly": 999.00,
                "price_yearly": 9990.00,
                "max_projects": 1000,
                "storage_gb": 1000,
                "cpu_cores": 32,
                "gpu_vram_gb": 64,
                "has_watermark": False,
                "requires_citation": False,
                "requires_archive": False,
                "has_priority_support": True,
                "has_custom_integrations": True,
                "has_team_collaboration": True,
                "is_featured": False,
                "is_active": True,
                "display_order": 5,
            },
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.update_or_create(
                plan_type=plan_data["plan_type"], defaults=plan_data
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Updated plan: {plan.name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {created_count + updated_count} plans "
                f"({created_count} created, {updated_count} updated)"
            )
        )
