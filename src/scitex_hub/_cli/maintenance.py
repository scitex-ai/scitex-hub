"""Local operator controls; no remote or user-data operations."""

import json
from dataclasses import asdict

import click

from scitex_hub._logging import get_console
from scitex_hub.maintenance import DEFAULT_MESSAGE, read_state, write_state


@click.group()
@click.option(
    "--state-file",
    envvar="SCITEX_HUB_MAINTENANCE_FILE",
    required=True,
    type=click.Path(path_type=str),
    help="Operator-owned local state file shared by web workers.",
)
@click.pass_context
def maintenance(ctx, state_file):
    """Control request admission without restarting Hub."""
    ctx.ensure_object(dict)
    ctx.obj["maintenance_file"] = state_file


def _output(ctx, state, as_json):
    if as_json or ctx.obj.get("json", False):
        click.echo(json.dumps(asdict(state)))
    else:
        get_console(__name__).info(
            "Maintenance: " + ("enabled" if state.enabled else "disabled")
        )


@maintenance.command("status")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def status(ctx, as_json):
    """Read the local admission state."""
    state = read_state(ctx.obj["maintenance_file"])
    _output(ctx, state, as_json)
    if not state.valid:
        raise click.ClickException(
            "Maintenance state is unreadable or invalid; admission is closed."
        )


@maintenance.command("enable")
@click.option("--message", default=DEFAULT_MESSAGE)
@click.option("--retry-after", type=click.IntRange(1, 86400), default=300)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def enable(ctx, message, retry_after, as_json):
    """Close new HTTP/WebSocket admission. Does not drain running jobs."""
    _write(ctx, True, message, retry_after, as_json)


@maintenance.command("disable")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def disable(ctx, as_json):
    """Reopen request admission after storage and service checks."""
    _write(ctx, False, DEFAULT_MESSAGE, 300, as_json)


def _write(ctx, enabled, message, retry_after, as_json):
    try:
        state = write_state(
            ctx.obj["maintenance_file"],
            enabled=enabled,
            message=message,
            retry_after=retry_after,
        )
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    _output(ctx, state, as_json)
