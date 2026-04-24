#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/context.py
"""Context commands for scitex-cloud CLI."""

import json

import click


@click.group()
def context():
    """Web app context for AI agents.

    \b
    Query web app state, evaluate JS, and drive browser UI.

    \b
    Examples:
        scitex-cloud context get                # Get full context
        scitex-cloud context get --page /writer/ # Context for writer page
        scitex-cloud context eval "document.title"
    """


@context.command("get")
@click.option("--page", default="", help="Current page URL (e.g. /writer/)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def context_get(page, as_json):
    """Get web app context: username, page, skills, available actions."""
    from .._api import CloudClient

    client = CloudClient()
    result = client.get_context(page)

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        click.echo(click.style("Web App Context", fg="cyan", bold=True))
        click.echo(f"  Username: {result.get('username', 'N/A')}")
        click.echo(f"  Page: {result.get('page', '(none)')}")

        skill = result.get("active_skill")
        if skill:
            click.echo(f"  Active Skill: {skill.get('display_name', 'N/A')}")

        skills = result.get("all_skills", {})
        if skills:
            click.echo(f"  Registered Skills: {len(skills)}")
            for name, s in sorted(skills.items()):
                click.echo(f"    - {s.get('display_name', name)}")

        actions = result.get("available_actions", [])
        if actions:
            click.echo(f"  Actions: {', '.join(actions)}")

        media = result.get("media_rendering", [])
        if media:
            click.echo(f"  Media: {', '.join(media)}")


@context.command("eval")
@click.argument("code")
@click.option("--timeout", type=int, default=10, help="Timeout in seconds (max 30)")
def context_eval(code, timeout):
    """Evaluate JavaScript in the user's browser."""
    from .._api import CloudClient

    client = CloudClient()
    result = client.eval_js(code, timeout)

    if result.get("success"):
        click.echo(result.get("result", ""))
    else:
        click.echo(click.style(f"Error: {result.get('error')}", fg="red"), err=True)


@context.command("trigger-action")
@click.argument("steps_json")
@click.option("--delay", type=int, default=900, help="Delay between steps (ms)")
def context_action(steps_json, delay):
    """Send UI action steps to the browser.

    STEPS_JSON is a JSON array of action dicts.
    """
    try:
        steps = json.loads(steps_json)
    except json.JSONDecodeError:
        click.echo(click.style("Error: Invalid JSON", fg="red"), err=True)
        return

    from .._api import CloudClient

    client = CloudClient()
    result = client.ui_action(steps, delay)

    if result.get("success"):
        click.echo(f"Sent {result.get('steps_sent', 0)} steps")
    else:
        click.echo(click.style(f"Error: {result.get('error')}", fg="red"), err=True)


# EOF
