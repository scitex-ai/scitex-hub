#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/main.py

"""Main CLI entry point for scitex-cloud."""

import click

from .. import __version__
from .deploy import deploy
from .docker import docker
from .setup import setup
from .status import logs, status


@click.group()
@click.version_option(version=__version__, prog_name="scitex-cloud")
@click.pass_context
def main(ctx):
    """SciTeX Cloud - Deployment and management CLI.

    Manage SciTeX Cloud deployments with simple commands.

    \b
    Examples:
        scitex-cloud setup --env dev     # Setup development environment
        scitex-cloud deploy              # Deploy with current settings
        scitex-cloud docker up           # Start containers
        scitex-cloud status              # Show deployment status
    """
    ctx.ensure_object(dict)


# Register command groups
main.add_command(setup)
main.add_command(deploy)
main.add_command(docker)
main.add_command(status)
main.add_command(logs)


if __name__ == "__main__":
    main()

# EOF
