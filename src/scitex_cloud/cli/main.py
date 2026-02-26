#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/main.py

"""Main CLI entry point for scitex-cloud."""

import click
from rich.console import Console

from .. import __version__
from .completion import completion
from .context import context as context_group
from .deploy import deploy
from .docker import docker
from .gitea import gitea
from .mcp import mcp
from .setup import setup
from .status import logs, status

console = Console()

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _print_recursive_help(ctx, param, value):
    """Callback for --help-recursive flag."""
    if not value or ctx.resilient_parsing:
        return

    def _print_command_help(cmd, prefix: str, parent_ctx):
        """Recursively print help for a command and its subcommands."""
        console.print(f"\n[bold cyan]━━━ {prefix} ━━━[/bold cyan]")
        sub_ctx = click.Context(cmd, info_name=prefix.split()[-1], parent=parent_ctx)
        console.print(cmd.get_help(sub_ctx))

        if isinstance(cmd, click.Group):
            for sub_name, sub_cmd in sorted(cmd.commands.items()):
                _print_command_help(sub_cmd, f"{prefix} {sub_name}", sub_ctx)

    # Print main help
    console.print("[bold cyan]━━━ scitex-cloud ━━━[/bold cyan]")
    console.print(ctx.get_help())

    # Print all subcommands recursively
    for name, cmd in sorted(main.commands.items()):
        _print_command_help(cmd, f"scitex-cloud {name}", ctx)

    ctx.exit(0)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, prog_name="scitex-cloud")
@click.option(
    "--help-recursive",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_print_recursive_help,
    help="Show help for all commands recursively.",
)
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
        scitex-cloud mcp start           # Start MCP server
    """
    ctx.ensure_object(dict)


# Register command groups
main.add_command(setup)
main.add_command(deploy)
main.add_command(docker)
main.add_command(gitea)
main.add_command(mcp)
main.add_command(context_group, "context")
main.add_command(status)
main.add_command(logs)
main.add_command(completion)


@main.command("list-python-apis", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-v", "--verbose", count=True, help="Verbosity: -v sig, -vv +doc, -vvv full"
)
@click.option("-d", "--max-depth", type=int, default=5, help="Max recursion depth")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_python_apis(verbose, max_depth, as_json):
    """List Python APIs (alias for: scitex introspect api scitex_cloud)."""
    try:
        from scitex.cli.introspect import api

        ctx = click.Context(api)
        ctx.invoke(
            api,
            dotted_path="scitex_cloud",
            verbose=verbose,
            max_depth=max_depth,
            as_json=as_json,
        )
    except ImportError:
        # Fallback if scitex not installed
        click.echo("Install scitex for full API introspection:")
        click.echo("  pip install scitex")
        click.echo()
        click.echo("Or use: scitex introspect api scitex_cloud")


if __name__ == "__main__":
    main()

# EOF
