#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Home "Getting started" checklist (card hub-first-10-minutes-onboarding-flow-20260914)."""

import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import translation

from apps.infra.llm_app.models import ChatMessage, ChatSession
from apps.infra.project_app.models import Project
from apps.workspace.apps_app.models import FirstRunProgress
from apps.workspace.apps_app.services.first_run import (
    checklist_context,
    mark_step_done,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _new_user(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="TestPass123!",  # pragma: allowlist secret
    )


class FirstRunChecklistTest(TestCase):
    def test_new_user_sees_the_checklist_on_home(self):
        # Arrange
        self.client.force_login(_new_user("first-run-new"))
        # Act
        response = self.client.get("/")
        # Assert
        assert b'id="first-run-checklist"' in response.content

    def test_following_step_one_after_a_project_exists_marks_it_done(self):
        # Arrange
        user = _new_user("first-run-project")
        Project.objects.create(name="First", slug="first", owner=user)
        self.client.force_login(user)
        # Act
        self.client.get("/apps/getting-started/create_project/")
        # Assert
        assert "create_project" in FirstRunProgress.objects.get(user=user).completed_steps

    def test_dismissed_checklist_stays_collapsed(self):
        # Arrange
        user = _new_user("first-run-dismiss")
        self.client.force_login(user)
        self.client.post("/apps/getting-started/dismiss/")
        # Act
        response = self.client.get("/")
        # Assert
        assert response.context["first_run"]["is_collapsed"] is True

    def test_owning_a_project_completes_step_one_without_following_it(self):
        # Arrange
        user = _new_user("first-run-owner")
        Project.objects.create(name="Paper", slug="paper", owner=user)
        # Act
        steps = {step["key"]: step["done"] for step in checklist_context(user)["steps"]}
        # Assert
        assert steps["create_project"] is True

    def test_the_dotfiles_project_alone_does_not_complete_step_one(self):
        # Arrange
        user = _new_user("first-run-dotfiles")
        Project.objects.get_or_create(
            owner=user, is_home=True, defaults={"name": "dotfiles", "slug": "dotfiles"}
        )
        # Act
        steps = {step["key"]: step["done"] for step in checklist_context(user)["steps"]}
        # Assert
        assert steps["create_project"] is False

    def test_a_chat_message_completes_the_ask_agent_step(self):
        # Arrange
        user = _new_user("first-run-chat")
        session = ChatSession.objects.create(user=user)
        ChatMessage.objects.create(session=session, role="user", text="Hello")
        # Act
        steps = {step["key"]: step["done"] for step in checklist_context(user)["steps"]}
        # Assert
        assert steps["ask_agent"] is True

    def test_home_renders_the_phone_collapsible_card(self):
        # Arrange
        self.client.force_login(_new_user("first-run-phone"))
        # Act
        response = self.client.get("/")
        # Assert
        assert b"first-run--phone-collapsible" in response.content

    def test_dont_show_again_keeps_the_card_off_home(self):
        # Arrange
        user = _new_user("first-run-forever")
        self.client.force_login(user)
        self.client.post("/apps/getting-started/dismiss/", {"forever": "1"})
        # Act
        response = self.client.get("/")
        # Assert
        assert b'id="first-run-checklist"' not in response.content

    def test_reshow_clears_dont_show_again(self):
        # Arrange
        user = _new_user("first-run-reshow")
        self.client.force_login(user)
        self.client.post("/apps/getting-started/dismiss/", {"forever": "1"})
        # Act
        self.client.post("/apps/getting-started/reshow/")
        # Assert
        assert FirstRunProgress.objects.get(user=user).hidden_at is None

    def test_progress_of_another_user_is_isolated(self):
        # Arrange
        finisher = _new_user("first-run-finisher")
        newcomer = _new_user("first-run-newcomer")
        mark_step_done(finisher, "add_references")
        # Act
        newcomer_steps = {step["key"]: step["done"] for step in checklist_context(newcomer)["steps"]}
        # Assert
        assert newcomer_steps["add_references"] is False


@pytest.fixture(name="compiled_catalogs")
def _compiled_catalogs():
    script = _REPO_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    subprocess.run([sys.executable, str(script)], cwd=_REPO_ROOT, check=True)
    translation.trans_real._translations.clear()
    yield
    translation.trans_real._translations.clear()


@pytest.mark.django_db
def test_checklist_title_renders_in_japanese(compiled_catalogs):
    # Arrange
    first_run = checklist_context(_new_user("first-run-ja"))
    # Act
    with translation.override("ja"):
        html = render_to_string(
            "apps_app/partials/first_run_checklist.html", {"first_run": first_run}
        )
    # Assert
    assert "はじめに" in html


# EOF
