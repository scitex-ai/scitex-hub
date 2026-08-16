#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/context.py
"""Context commands for scitex-hub CLI."""

import json

import click

from ._flags import (
    confirm_or_abort,
    emit_json,
    json_flag,
    mutating_flags,
    print_dry_run,
)


@click.group()
def context():
    """Web app context for AI agents.

    \b
    Query web app state, evaluate JS, and drive browser UI.

    \b
    Example:
        scitex-hub context get                 # Get full context
        scitex-hub context get --page /writer/ # Context for writer page
        scitex-hub context eval "document.title"
        scitex-hub context trigger-action '[{"action":"click","selector":"#go"}]'
    """


@context.command("get")
@click.option("--page", default="", help="Current page URL (e.g. /writer/)")
@json_flag()
def context_get(page, json_output):
    """Get web app context: username, page, skills, available actions.

    \b
    Example:
        scitex-hub context get
        scitex-hub context get --page /writer/
        scitex-hub context get --json
    """
    from .._api import CloudClient

    client = CloudClient()
    result = client.get_context(page)

    if json_output:
        emit_json(result)
        return

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
@mutating_flags()
def context_eval(code, timeout, dry_run, yes):
    """Evaluate JavaScript in the user's browser.

    Executes ``code`` remotely; the result is whatever the JS expression
    returns. This is a side-effectful operation (mutating verb): it may
    drive the user's browser, so ``--dry-run`` / ``--yes`` apply.

    \b
    Example:
        scitex-hub context eval "document.title"
        scitex-hub context eval "window.scrollTo(0, 0)" --yes
        scitex-hub context eval "document.title" --dry-run
    """
    if dry_run:
        print_dry_run(f"evaluate JS in user's browser (timeout={timeout}s): {code!r}")
        return

    confirm_or_abort(
        f"Evaluate JS in user's browser: {code!r}?",
        yes=yes,
        dry_run=dry_run,
    )

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
@mutating_flags()
def context_action(steps_json, delay, dry_run, yes):
    """Send UI action steps to the browser.

    STEPS_JSON is a JSON array of action dicts.

    \b
    Example:
        scitex-hub context trigger-action '[{"action":"click","selector":"#go"}]'
        scitex-hub context trigger-action '[{"action":"type","text":"hi"}]' --delay 500
        scitex-hub context trigger-action '[{"action":"click","selector":"#go"}]' --yes
    """
    try:
        steps = json.loads(steps_json)
    except json.JSONDecodeError:
        click.echo(click.style("Error: Invalid JSON", fg="red"), err=True)
        raise SystemExit(1)

    if dry_run:
        print_dry_run(
            f"send {len(steps)} UI action step(s) to browser "
            f"(delay={delay}ms): {steps_json}"
        )
        return

    confirm_or_abort(
        f"Send {len(steps)} UI action step(s) to user's browser?",
        yes=yes,
        dry_run=dry_run,
    )

    from .._api import CloudClient

    client = CloudClient()
    result = client.ui_action(steps, delay)

    if result.get("success"):
        click.echo(f"Sent {result.get('steps_sent', 0)} steps")
    else:
        click.echo(click.style(f"Error: {result.get('error')}", fg="red"), err=True)


# EOF
