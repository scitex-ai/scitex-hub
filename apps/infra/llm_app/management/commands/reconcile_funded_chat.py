from django.core.management.base import BaseCommand, CommandError

from apps.infra.llm_app.funded_chat.config import FundedChatConfig
from apps.infra.llm_app.funded_chat.service import FundedChatService


class Command(BaseCommand):
    help = "Reconcile durable funded-chat requests without contacting a provider"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit <= 0 or limit > 10_000:
            raise CommandError("--limit must be between 1 and 10000")
        # Reconciliation uses only persisted request/provider identities and does
        # not need an enabled provider or access to its credential.
        config = FundedChatConfig(enabled=False, provider="", model="", api_key="")
        count = FundedChatService(config=config).reconcile_stale_requests(limit=limit)
        self.stdout.write(f"reconciled={count}")
