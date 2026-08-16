"""CLI for Live Paper — standalone GUI launcher."""

import click


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Live Paper — SciTeX Cloud App."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.option("--port", "-p", default=8050, help="Server port")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind")
@click.option("--no-browser", is_flag=True, help="Don't open browser")
@click.option("--force", is_flag=True, help="Kill existing process on port")
def gui(port, host, no_browser, force):
    """Launch standalone GUI with workspace shell."""
    if force:
        import subprocess

        subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            capture_output=True,
        )

    from scitex_app._standalone import run_standalone

    run_standalone(
        app_module="scitex_live_paper_hub_app",
        port=port,
        host=host,
        open_browser=not no_browser,
    )
