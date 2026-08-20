#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grammar guards for ``scitex-hub account *``.

Phase-1 PR-4 of operator-12909's token+CLI surface. These tests pin
the CLI verb tree against scitex-dev's convention doctrine (msg
548d1e6e) so a future "cleanup" PR can't silently drop or rename a
verb the user-runbook + skills documentation depends on.

No mocks. Uses Click's command-introspection API to walk the tree
the way ``scitex-dev ecosystem audit-cli`` does at the convention-audit
boundary.
"""

from __future__ import annotations

import click


def _params(cmd: click.Command) -> set[str]:
    """Return the set of declared option/argument names for ``cmd``."""
    return {p.name for p in cmd.params}


def test_account_group_exists():
    # Arrange
    from scitex_hub._cli._account import account

    # Act
    actual = isinstance(account, click.Group)

    # Assert
    assert actual is True


def test_account_subgroups_include_token():
    # Arrange
    from scitex_hub._cli._account import account

    # Act
    actual = "token" in account.commands

    # Assert
    assert actual is True


def test_account_token_subgroup_has_three_verbs():
    # Arrange
    from scitex_hub._cli._account import account

    token_group = account.commands["token"]

    # Act
    verbs = set(token_group.commands)

    # Assert
    assert verbs == {"create", "list", "revoke"}


def test_account_token_create_accepts_user_password_scope_name_server():
    # Arrange
    from scitex_hub._cli._account import account

    create_cmd = account.commands["token"].commands["create"]

    # Act
    params = _params(create_cmd)

    # Assert — every parameter the runbook (and scitex-dev's grammar
    # doctrine) names must exist; missing any of these breaks the docs.
    assert {"user", "password", "scopes", "name", "server", "save"} <= params


def test_account_token_revoke_requires_yes_flag():
    # Arrange
    from scitex_hub._cli._account import account

    revoke_cmd = account.commands["token"].commands["revoke"]

    # Act
    params = _params(revoke_cmd)

    # Assert — destructive verb MUST gate on --yes per the spec §2
    # destructive-action rule (no interactive prompt).
    assert "yes" in params and "token_id" in params


def test_account_has_whoami_polysemous_leaf():
    # Arrange
    from scitex_hub._cli._account import account

    # Act
    actual = "whoami" in account.commands

    # Assert
    assert actual is True


def test_account_has_doctor_health_check_leaf():
    # Arrange
    from scitex_hub._cli._account import account

    # Act
    actual = "doctor" in account.commands

    # Assert
    assert actual is True


def test_account_top_level_does_not_expose_login_verb():
    # Arrange — bare-top-level `login` was explicitly rejected by dev
    # (msg 548d1e6e: "REJECT scitex-hub login — bare top-level
    # intransitive login, not in the §1b exception list, audit-cli
    # blocks it"). This guards against a future PR reintroducing it.
    from scitex_hub._cli.main import main

    # Act
    top_level_verbs = set(main.commands)

    # Assert
    assert "login" not in top_level_verbs


def test_main_cli_registers_account_group():
    # Arrange
    from scitex_hub._cli.main import main

    # Act
    actual = "account" in main.commands

    # Assert
    assert actual is True


# EOF
