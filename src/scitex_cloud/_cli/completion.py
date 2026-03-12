#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/completion.py

"""Shell completion commands for scitex-cloud CLI."""

import click


@click.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell):
    """Generate shell completion script.

    \b
    Generate and install shell completion for scitex-cloud CLI.

    \b
    Usage:
        # Bash (add to ~/.bashrc)
        eval "$(scitex-cloud completion bash)"

        # Zsh (add to ~/.zshrc)
        eval "$(scitex-cloud completion zsh)"

        # Fish (add to ~/.config/fish/completions/)
        scitex-cloud completion fish > ~/.config/fish/completions/scitex-cloud.fish

    \b
    Examples:
        scitex-cloud completion bash    # Output bash completion script
        scitex-cloud completion zsh     # Output zsh completion script
        scitex-cloud completion fish    # Output fish completion script
    """

    # Get the shell completion from Click
    from click.shell_completion import get_completion_class

    comp_cls = get_completion_class(shell)
    if comp_cls is None:
        raise click.ClickException(f"Shell '{shell}' is not supported.")

    # Import the main CLI to get completions
    from .main import main

    comp = comp_cls(main, {}, "scitex-cloud", "_SCITEX_CLOUD_COMPLETE")
    click.echo(comp.source())


# EOF
