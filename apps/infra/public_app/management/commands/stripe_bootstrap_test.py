"""Create or look up the Stripe products and prices for the online plans.

Reads the subscription rows of pricing.json (USD, tax-inclusive), makes each
exist in the Stripe account behind SCITEX_HUB_STRIPE_SECRET_KEY, and prints the
SCITEX_HUB_STRIPE_PRICE_* env lines. Output is IDs only, never a secret.
Safe to re-run: products use a fixed id and prices a lookup_key.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.infra.public_app.services.billing_provider import subscription_pricing_rows
from apps.infra.public_app.services.stripe_setup import build_stripe_client

LIVE_KEY_PREFIXES = ("sk_live_", "rk_live_")


def stripe_price_env_name(pricing_id: str) -> str:
    return settings.STRIPE_PRICE_ENV_PREFIX + pricing_id.upper().replace("-", "_")


def ensure_product(stripe_client, row):
    product_id = f"scitex-{row['id']}"
    existing = stripe_client.Product.list(ids=[product_id], limit=1).data
    if existing:
        return existing[0]
    return stripe_client.Product.create(
        id=product_id,
        name=row["label"],
        description=row.get("description", ""),
        metadata={"pricing_id": row["id"]},
    )


def ensure_price(stripe_client, row, product):
    amount_cents = int(round(row["amount"] * 100))
    # The amount is part of the key, so a pricing.json change yields a new price.
    lookup_key = f"{row['id']}-usd-{row['unit']}-{amount_cents}"
    existing = stripe_client.Price.list(lookup_keys=[lookup_key], limit=1).data
    if existing:
        return existing[0]
    return stripe_client.Price.create(
        product=product.id,
        currency="usd",
        unit_amount=amount_cents,
        recurring={"interval": row["unit"]},
        tax_behavior="inclusive",
        lookup_key=lookup_key,
        metadata={"pricing_id": row["id"]},
    )


def bootstrap_catalog(stripe_client) -> list[str]:
    """Ensure every online plan exists in Stripe; return the env lines to add."""
    env_lines = []
    for row in subscription_pricing_rows():
        product = ensure_product(stripe_client, row)
        price = ensure_price(stripe_client, row, product)
        env_lines.append(f"{stripe_price_env_name(row['id'])}={price.id}")
    return env_lines


class Command(BaseCommand):
    help = "Create or look up Stripe TEST products/prices from pricing.json and print the env lines."

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            help="Allow a live secret key (creates real catalog objects).",
        )

    def handle(self, *args, **options):
        secret_key = settings.STRIPE_SECRET_KEY
        if not secret_key:
            raise CommandError("SCITEX_HUB_STRIPE_SECRET_KEY is not set.")
        if secret_key.startswith(LIVE_KEY_PREFIXES) and not options["live"]:
            raise CommandError(
                "SCITEX_HUB_STRIPE_SECRET_KEY is a LIVE key. Use a test key "
                "(sk_test_...), or pass --live if you really mean the live account."
            )

        env_lines = bootstrap_catalog(build_stripe_client(secret_key))
        self.stdout.write("# Add to the environment (SECRET/.env.*):")
        for line in env_lines:
            self.stdout.write(line)
