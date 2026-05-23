#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/completion.py

"""Shell completion commands for scitex-hub CLI."""

import click


@click.group("completion", invoke_without_command=True)
@click.pass_context
def completion_group(ctx):
    """Shell tab-completion commands for scitex-hub.

    \b
    Examples:
        scitex-hub completion print-script --shell bash
        eval "$(scitex-hub completion print-script --shell bash)"
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@completion_group.command("print-script")
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish"]),
    default="bash",
    help="Target shell. Default: bash.",
)
def print_script(shell):
    """Print the completion script for the chosen shell to stdout."""

    # Get the shell completion from Click
    from click.shell_completion import get_completion_class

    comp_cls = get_completion_class(shell)
    if comp_cls is None:
        raise click.ClickException(f"Shell '{shell}' is not supported.")

    # Import the main CLI to get completions
    from .main import main

    comp = comp_cls(main, {}, "scitex-hub", "_SCITEX_CLOUD_COMPLETE")
    click.echo(comp.source())


# EOF
