#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/main.py

"""Main CLI entry point for scitex-hub."""

import click
from rich.console import Console

from .. import __version__
from ._click_compat import (
    HAS_CLI_HELPERS,
    register_error_redirect,
    register_warn_alias,
    spec_group_kwargs,
)
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

# Doctrine §4a — the canonical seven-category help order. `Other` is the
# auto catch-all and must stay empty: every visible root command is
# assigned explicitly below.
_ROOT_CATEGORIES = [
    (
        "Core",
        [
            "init",
            "deploy",
            "project",
            "app",
            "workspace",
            "account",
            "auth",
            "context",
        ],
    ),
    ("Data & Sync", ["push-project", "pull-project", "gitea"]),
    ("Service", ["docker", "mcp", "sdk"]),
    ("Diagnostics", ["status", "logs"]),
    ("Introspection", ["list-python-apis", "skills", "docs", "dev"]),
    (
        "Shell",
        ["completion", "install-shell-completion", "print-shell-completion"],
    ),
]


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


@click.group(
    context_settings=CONTEXT_SETTINGS,
    **spec_group_kwargs(
        summary="Deployment and management CLI.",
        version_of="scitex-hub",
        description=(
            "Config path resolution: config.yaml -> $SCITEX_HUB_CONFIG "
            "-> ~/.scitex/hub/config.yaml -> defaults.",
        ),
        examples=(
            ("{prog} init --env dev", "Initialize the dev environment"),
            ("{prog} deploy", "Deploy with current settings"),
            ("{prog} docker up", "Start containers"),
            ("{prog} status", "Show deployment status"),
            ("{prog} mcp start", "Start MCP server"),
        ),
        command_categories=_ROOT_CATEGORIES,
    ),
)
@click.version_option(__version__, "-V", "--version", prog_name="scitex-hub")
@click.option(
    "--help-recursive",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_print_recursive_help,
    help="Show help for all commands recursively.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help=(
        "Emit machine-readable JSON output (propagates to subcommands that "
        "honour it; see `<verb> --json`)."
    ),
)
@click.pass_context
def main(ctx, json_output):
    """SciTeX Hub - Deployment and management CLI.

    Config path resolution:
      config.yaml -> $SCITEX_HUB_CONFIG -> ~/.scitex/hub/config.yaml -> defaults

    \b
    Example:
        scitex-hub init --env dev      # Initialize development environment
        scitex-hub deploy              # Deploy with current settings
        scitex-hub docker up           # Start containers
        scitex-hub status              # Show deployment status
        scitex-hub mcp start           # Start MCP server
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output


# ── Command registration ──
#
# Slice 6a pilot verb renames (doctrine §1d; deprecation ladder §11):
# the canonical short verbs are registered directly and every old
# spelling becomes a warn-phase deprecated alias (removed in v0.20).
# `setup` was already an error-phase redirect, so it stays on the error
# rung, retargeted at `init`.

main.add_command(app)

main.add_command(setup)  # canonical name: init (see setup.py)
register_warn_alias(main, "setup-environment", target="init", remove_in="v0.20")
register_error_redirect(main, "setup", target="init", remove_in="v0.20")

main.add_command(deploy)
register_warn_alias(main, "deploy-project", target="deploy", remove_in="v0.20")

main.add_command(docker)
main.add_command(gitea)
main.add_command(mcp)
main.add_command(context_group, "context")

main.add_command(status)
register_warn_alias(main, "show-status", target="status", remove_in="v0.20")

main.add_command(logs)
register_warn_alias(main, "show-logs", target="logs", remove_in="v0.20")

main.add_command(completion)
main.add_command(workspace)
main.add_command(sdk)

from ._account import account  # noqa: E402
from ._auth import auth  # noqa: E402
from .project import project  # noqa: E402
from .sync import register_sync_commands  # noqa: E402

main.add_command(account)
main.add_command(auth)
main.add_command(project)
register_sync_commands(main)


@main.command("list-python-apis", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-v", "--verbose", count=True, help="Verbosity: -v sig, -vv +doc, -vvv full"
)
@click.option("-d", "--max-depth", type=int, default=5, help="Max recursion depth")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_python_apis(verbose, max_depth, as_json):
    """List Python APIs (alias for: scitex introspect api scitex_hub).

    \b
    Example:
        scitex-hub list-python-apis
        scitex-hub list-python-apis -v
        scitex-hub list-python-apis --json
        scitex-hub list-python-apis -d 3 -vv
    """
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


# audit §4 — inject version into root --help. With the spec-built help
# active (SpecGroup + CliHelp.version_of) the version already renders in
# the summary line, so this fallback only applies on a released
# scitex-dev that predates help_spec.
if not HAS_CLI_HELPERS:
    try:
        from importlib.metadata import version as _v

        main.help = f"scitex-hub (v{_v('scitex-hub')}) — " + (main.help or "").lstrip()
    except Exception:
        pass
