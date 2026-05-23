#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/main.py

"""Main CLI entry point for scitex-hub."""

import click
from rich.console import Console

from .. import __version__
from .app import app  # noqa: F401
from .completion import completion_group as completion
from .context import context as context_group
from .deploy import deploy
from .docker import docker
from .gitea import gitea
from .mcp import mcp
from .sdk import sdk  # noqa: F401
from .setup import setup
from .status import logs, status
from .workspace import workspace  # noqa: F401

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
    console.print("[bold cyan]━━━ scitex-hub ━━━[/bold cyan]")
    console.print(ctx.get_help())

    # Print all subcommands recursively
    for name, cmd in sorted(main.commands.items()):
        _print_command_help(cmd, f"scitex-hub {name}", ctx)

    ctx.exit(0)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, prog_name="scitex-hub")
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
        scitex-hub setup --env dev     # Setup development environment
        scitex-hub deploy              # Deploy with current settings
        scitex-hub docker up           # Start containers
        scitex-hub status              # Show deployment status
        scitex-hub mcp start           # Start MCP server
    """
    ctx.ensure_object(dict)


# ── Deprecation-redirect helper (noun-verb convention §5) ──


def _dep(old: str, new: str):
    @click.pass_context
    def _impl(ctx, **_):
        click.echo(
            f"error: `scitex-hub {old}` was renamed to `scitex-hub {new}`.\n"
            f"Re-run with: scitex-hub {new} [...]",
            err=True,
        )
        ctx.exit(2)

    return click.command(
        old,
        hidden=True,
        context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    )(_impl)


# Register command groups (renamed to verb-noun compound leaves where bare)
main.add_command(app)

setup.name = "setup-environment"
main.add_command(setup)
main.add_command(_dep("setup", "setup-environment"))

deploy.name = "deploy-project"
main.add_command(deploy)
main.add_command(_dep("deploy", "deploy-project"))

main.add_command(docker)
main.add_command(gitea)
main.add_command(mcp)
main.add_command(context_group, "context")

status.name = "show-status"
main.add_command(status)
main.add_command(_dep("status", "show-status"))

logs.name = "show-logs"
main.add_command(logs)
main.add_command(_dep("logs", "show-logs"))

main.add_command(completion)
main.add_command(workspace)
main.add_command(sdk)

from .project import project  # noqa: E402
from .sync import register_sync_commands  # noqa: E402

main.add_command(project)
register_sync_commands(main)


@main.command("list-python-apis", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-v", "--verbose", count=True, help="Verbosity: -v sig, -vv +doc, -vvv full"
)
@click.option("-d", "--max-depth", type=int, default=5, help="Max recursion depth")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_python_apis(verbose, max_depth, as_json):
    """List Python APIs (alias for: scitex introspect api scitex_hub)."""
    try:
        from scitex.cli.introspect import api

        ctx = click.Context(api)
        ctx.invoke(
            api,
            dotted_path="scitex_hub",
            verbose=verbose,
            max_depth=max_depth,
            as_json=as_json,
        )
    except ImportError:
        # Fallback if scitex not installed
        click.echo("Install scitex for full API introspection:")
        click.echo("  pip install scitex")
        click.echo()
        click.echo("Or use: scitex introspect api scitex_hub")


try:
    from scitex_dev.cli import skills_click_group

    main.add_command(skills_click_group(package="scitex-hub"))
except ImportError:
    pass


# §1a: install-shell-completion + print-shell-completion (canonical leaves)
try:
    from scitex_dev._cli._completion import attach_shell_completion

    attach_shell_completion(main, prog_name="scitex-hub")
except ImportError:
    pass


# audit-cli §1a — packages with _skills/ MUST expose
# `<cli> skills {list,get,install}`.
from ._skills import skills_group as _skills_group

main.add_command(_skills_group, name="skills")

if __name__ == "__main__":
    main()

# EOF


# audit §4 — inject version into root --help
try:
    from importlib.metadata import version as _v

    main.help = f"scitex-hub (v{_v('scitex-hub')}) — " + (main.help or "").lstrip()
except Exception:
    pass
