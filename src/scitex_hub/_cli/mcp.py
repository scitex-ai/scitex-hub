#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/mcp.py
"""MCP CLI subcommands for scitex-hub."""

import sys

import click

from ._click_compat import spec_command_kwargs, spec_group_kwargs
from ._flags import (
    confirm_or_abort,
    emit_json,
    json_flag,
    mutating_flags,
    print_dry_run,
)

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(
    context_settings=CONTEXT_SETTINGS,
    **spec_group_kwargs(summary="MCP (Model Context Protocol) server commands."),
)
def mcp():
    """MCP (Model Context Protocol) server commands.

    \b
    Commands:
      start        - Start the MCP server
      doctor       - Diagnose MCP setup
      installation - Show installation instructions
      list-tools   - List available MCP tools
    """
    pass


@mcp.command(
    "start",
    context_settings=CONTEXT_SETTINGS,
    **spec_command_kwargs(
        summary="Start the MCP server.",
        examples=(
            ("{prog} mcp start -t http --port 8086 --yes", "Serve over HTTP."),
        ),
    ),
)
@click.option(
    "-t",
    "--transport",
    type=click.Choice(["stdio", "sse", "http"]),
    default="stdio",
    help="Transport protocol (http recommended for remote)",
)
@click.option(
    "--host",
    default="0.0.0.0",
    envvar="SCITEX_HUB_MCP_HOST",
    help="Host for HTTP/SSE transport",
)
@click.option(
    "--port",
    default=8086,
    type=int,
    envvar="SCITEX_HUB_MCP_PORT",
    help="Port for HTTP/SSE transport",
)
@mutating_flags()
def mcp_start(transport: str, host: str, port: int, dry_run: bool, yes: bool):
    """Start the MCP server.

    \b
    Transports:
      stdio  - Standard I/O (default, for Claude Desktop local)
      http   - Streamable HTTP (recommended for remote/persistent)
      sse    - Server-Sent Events (deprecated as of MCP spec 2025-03-26)

    \b
    Local configuration (stdio):
      {
        "mcpServers": {
          "scitex-hub": {
            "command": "scitex-hub",
            "args": ["mcp", "start"]
          }
        }
      }

    \b
    Remote configuration (http):
      # Start server:
      scitex-hub mcp start -t http --host 0.0.0.0 --port 8086

      # Client config:
      {
        "mcpServers": {
          "scitex-hub-remote": {
            "url": "http://your-server:8086/mcp"
          }
        }
      }

    \b
    Example:
        scitex-hub mcp start
        scitex-hub mcp start -t http --host 0.0.0.0 --port 8086
        scitex-hub mcp start --dry-run
        scitex-hub mcp start -t http --yes
    """
    if dry_run:
        print_dry_run(f"start MCP server transport={transport} host={host} port={port}")
        return

    confirm_or_abort(
        f"Start MCP server (transport={transport}, host={host}, port={port})?",
        yes=yes,
        dry_run=dry_run,
    )

    run_mcp_server(transport, host, port)


@mcp.command(
    "doctor",
    context_settings=CONTEXT_SETTINGS,
    **spec_command_kwargs(
        summary="Diagnose MCP server setup and dependencies.",
        examples=(("{prog} mcp doctor", "Run the MCP diagnostics."),),
    ),
)
def mcp_doctor():
    """Diagnose MCP server setup and dependencies.

    \b
    Example:
        scitex-hub mcp doctor
    """
    click.echo("MCP Server Diagnostics")
    click.echo("=" * 50)
    click.echo()

    # Check fastmcp
    click.echo("Dependencies:")
    try:
        import fastmcp

        click.echo(
            f"  [OK] fastmcp installed (v{getattr(fastmcp, '__version__', 'unknown')})"
        )
    except ImportError:
        click.echo("  [FAIL] fastmcp not installed")
        click.echo("         Fix: pip install scitex-hub[mcp]")
        sys.exit(1)

    # Check requests
    try:
        import requests

        click.echo(
            f"  [OK] requests installed (v{getattr(requests, '__version__', 'unknown')})"
        )
    except ImportError:
        click.echo("  [FAIL] requests not installed")
        click.echo("         Fix: pip install scitex-hub[mcp]")
        sys.exit(1)

    # Check pyyaml (for gitea config)
    try:
        import yaml

        click.echo("  [OK] pyyaml installed")
    except ImportError:
        click.echo("  [WARN] pyyaml not installed (needed for gitea delete)")
        click.echo("         Fix: pip install scitex-hub[mcp]")

    click.echo()

    # Check tea CLI
    click.echo("Tea CLI (Gitea):")
    from pathlib import Path

    tea_path = Path.home() / ".local" / "bin" / "tea"
    if tea_path.exists():
        click.echo(f"  [OK] tea found at {tea_path}")
    else:
        click.echo("  [WARN] tea CLI not found")
        click.echo(
            "         Install: wget https://dl.gitea.com/tea/0.9.2/tea-0.9.2-linux-amd64 -O ~/.local/bin/tea && chmod +x ~/.local/bin/tea"
        )

    click.echo()

    # Check API configuration
    click.echo("API Configuration:")
    import os

    api_key = os.environ.get("SCITEX_HUB_API_KEY")
    base_url = os.environ.get("SCITEX_HUB_URL", "https://scitex.cloud")

    if api_key:
        click.echo("  [OK] SCITEX_HUB_API_KEY configured")
    else:
        click.echo(
            "  [WARN] SCITEX_HUB_API_KEY not set (needed for authenticated APIs)"
        )

    click.echo(f"  [OK] Base URL: {base_url}")

    click.echo()
    click.echo("All checks passed! MCP server is ready.")
    click.echo()
    click.echo("Start with:")
    click.echo("  scitex-hub mcp start              # stdio (Claude Desktop)")
    click.echo("  scitex-hub mcp start -t http      # HTTP transport")


@mcp.command(
    "installation",
    hidden=True,
    context_settings={"ignore_unknown_options": True},
)
@click.pass_context
def mcp_installation_deprecated(ctx):
    """(deprecated) Renamed to `install`."""
    click.echo(
        "error: `scitex-hub mcp installation` was renamed to "
        "`scitex-hub mcp install`.\n"
        "Re-run with: scitex-hub mcp install",
        err=True,
    )
    ctx.exit(2)


@mcp.command(
    "show-installation",
    hidden=True,
    context_settings={"ignore_unknown_options": True},
)
@click.pass_context
def mcp_show_installation_deprecated(ctx):
    """(deprecated) Renamed to `install`."""
    click.echo(
        "error: `scitex-hub mcp show-installation` was renamed to "
        "`scitex-hub mcp install`.\n"
        "Re-run with: scitex-hub mcp install",
        err=True,
    )
    ctx.exit(2)


@mcp.command(
    "install",
    context_settings=CONTEXT_SETTINGS,
    **spec_command_kwargs(
        summary="Show MCP client installation instructions.",
        examples=(("{prog} mcp install --yes", "Print client config snippets."),),
    ),
)
@mutating_flags()
def mcp_install(dry_run: bool, yes: bool):
    """Show MCP client installation instructions.

    (rename of show-installation)

    \b
    Example:
        scitex-hub mcp install
        scitex-hub mcp install --dry-run
        scitex-hub mcp install --yes
    """
    if dry_run:
        print_dry_run("print MCP client installation instructions to stdout")
        return

    confirm_or_abort(
        "Print MCP client installation instructions?", yes=yes, dry_run=dry_run
    )

    click.echo("MCP Client Configuration")
    click.echo("=" * 50)
    click.echo()
    click.echo("1. Local (stdio) - Claude Desktop / Claude Code:")
    click.echo()
    click.echo("   Add to your MCP client config (e.g., claude_desktop_config.json):")
    click.echo()
    click.echo("   {")
    click.echo('     "mcpServers": {')
    click.echo('       "scitex-hub": {')
    click.echo('         "command": "scitex-hub",')
    click.echo('         "args": ["mcp", "start"],')
    click.echo('         "env": {')
    click.echo(
        '           "SCITEX_HUB_API_KEY": "your-api-key"'
    )  # pragma: allowlist secret
    click.echo("         }")
    click.echo("       }")
    click.echo("     }")
    click.echo("   }")
    click.echo()
    click.echo("2. Remote (HTTP) - Persistent server:")
    click.echo()
    click.echo("   Server side:")
    click.echo("     scitex-hub mcp start -t http --host 0.0.0.0 --port 8086")
    click.echo()
    click.echo("   Client config:")
    click.echo("   {")
    click.echo('     "mcpServers": {')
    click.echo('       "scitex-hub-remote": {')
    click.echo('         "url": "http://your-server:8086/mcp"')
    click.echo("       }")
    click.echo("     }")
    click.echo("   }")
    click.echo()
    click.echo("Available tools: 23 (14 gitea + 9 cloud API)")
    click.echo("Run 'scitex-hub mcp list-tools' to see all tools.")


def _format_signature(tool_obj, indent: str = "  ") -> str:
    """Format tool as Python-like function signature."""
    params = []
    if hasattr(tool_obj, "parameters") and tool_obj.parameters:
        schema = tool_obj.parameters
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for name, info in props.items():
            ptype = info.get("type", "any")
            default = info.get("default")
            if name in required:
                p = f"{click.style(name, fg='white', bold=True)}: {click.style(ptype, fg='cyan')}"
            elif default is not None:
                def_str = repr(default) if len(repr(default)) < 20 else "..."
                p = f"{click.style(name, fg='white', bold=True)}: {click.style(ptype, fg='cyan')} = {click.style(def_str, fg='yellow')}"
            else:
                p = f"{click.style(name, fg='white', bold=True)}: {click.style(ptype, fg='cyan')} = {click.style('None', fg='yellow')}"
            params.append(p)
    name_s = click.style(tool_obj.name, fg="green", bold=True)
    return f"{indent}{name_s}({', '.join(params)})"


@mcp.command(
    "list-tools",
    context_settings=CONTEXT_SETTINGS,
    **spec_command_kwargs(
        summary="List available MCP tools.",
        examples=(("{prog} mcp list-tools -v", "List tools with signatures."),),
    ),
)
@click.option(
    "-v", "--verbose", count=True, help="Verbosity: -v sig, -vv +desc, -vvv full"
)
@json_flag()
def mcp_list_tools(verbose: int, json_output: bool):
    """List available MCP tools.

    \b
    Verbosity levels:
      (none)  - Tool names only
      -v      - Signatures
      -vv     - Signatures + one-line description
      -vvv    - Signatures + full description

    \b
    Example:
        scitex-hub mcp list-tools
        scitex-hub mcp list-tools -v
        scitex-hub mcp list-tools --json
    """
    as_json = json_output
    try:
        from .._mcp_server import FASTMCP_AVAILABLE
        from .._mcp_server import mcp as mcp_server
    except ImportError:
        click.secho("ERROR: Could not import MCP server", fg="red", err=True)
        click.echo("Install with: pip install scitex-hub[mcp]")
        raise SystemExit(1)

    if not FASTMCP_AVAILABLE or mcp_server is None:
        click.secho("ERROR: fastmcp not installed", fg="red", err=True)
        click.echo("Install with: pip install scitex-hub[mcp]")
        raise SystemExit(1)

    # Get tools (FastMCP 2.x/3.x compat via shared layer)
    from scitex_dev import get_tools_sync

    tools_dict = get_tools_sync(mcp_server)
    modules = {}
    for name in sorted(tools_dict.keys()):
        prefix = name.split("_")[0]
        if prefix not in modules:
            modules[prefix] = []
        modules[prefix].append(name)

    if as_json:
        output = {
            "name": "scitex-hub",
            "total": len(tools_dict),
            "modules": {
                mod: {
                    "count": len(tool_list),
                    "tools": [
                        {
                            "name": t,
                            "description": (
                                tools_dict[t].description if tools_dict.get(t) else ""
                            ),
                        }
                        for t in tool_list
                    ],
                }
                for mod, tool_list in modules.items()
            },
        }
        emit_json(output)
        return

    total = len(tools_dict)
    click.secho("SciTeX Hub MCP", fg="cyan", bold=True)
    click.echo(f"Tools: {total} ({len(modules)} modules)")
    click.echo()

    for mod, tool_list in sorted(modules.items()):
        click.secho(f"{mod}: {len(tool_list)} tools", fg="green", bold=True)
        for tool_name in tool_list:
            tool_obj = tools_dict.get(tool_name)

            if verbose == 0:
                click.echo(f"  {tool_name}")
            else:
                sig = _format_signature(tool_obj) if tool_obj else f"  {tool_name}"
                click.echo(sig)
                if verbose >= 2 and tool_obj and tool_obj.description:
                    desc = tool_obj.description.split("\n")[0].strip()
                    click.echo(f"    {desc}")
                    if verbose >= 3:
                        for line in tool_obj.description.strip().split("\n")[1:]:
                            click.echo(f"    {line}")
                    click.echo()
        click.echo()


def run_mcp_server(transport: str, host: str, port: int):
    """Internal function to run MCP server."""
    try:
        from .._mcp_server import run_server
    except ImportError:
        click.echo(
            "MCP server requires fastmcp. Install with:\n  pip install scitex-hub[mcp]",
            err=True,
        )
        sys.exit(1)

    run_server(transport=transport, host=host, port=port)


# EOF
