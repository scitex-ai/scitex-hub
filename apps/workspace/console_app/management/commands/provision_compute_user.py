"""Create a hub user's POSIX account on the compute nodes.

Usage:
    python manage.py provision_compute_user <username>             # print only
    python manage.py provision_compute_user <username> --execute   # run via ssh
"""

import shlex
import subprocess

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.workspace.console_app.services.compute_identity import (
    get_or_allocate_compute_identity,
)
from apps.workspace.console_app.services.compute_user import provision_commands

SSH_TIMEOUT_SECONDS = 60


class Command(BaseCommand):
    help = "Allocate a compute uid/gid and create the account on every compute node"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Run the ssh commands instead of printing them",
        )
        parser.add_argument(
            "--nodes",
            default="",
            help="Comma-separated nodes (default: SCITEX_HUB_COMPUTE_NODES); "
            "the first also runs sacctmgr and creates the home",
        )

    def handle(self, *args, **options):
        username = options["username"]
        try:
            user = get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist as e:
            raise CommandError(f"No hub user {username!r}") from e
        try:
            identity = get_or_allocate_compute_identity(user)
        except ValueError as e:
            raise CommandError(str(e)) from e

        nodes = [n.strip() for n in options["nodes"].split(",") if n.strip()] or None
        commands = provision_commands(username, identity.uid, identity.gid, nodes)
        self.stdout.write(f"# {username}: uid={identity.uid} gid={identity.gid}")
        for argv in commands:
            self.stdout.write(shlex.join(argv))
            if not options["execute"]:
                continue
            result = subprocess.run(
                argv, capture_output=True, text=True, timeout=SSH_TIMEOUT_SECONDS
            )
            if result.returncode != 0:
                raise CommandError(
                    f"{argv[1]} failed (rc={result.returncode}): "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
