#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ownership audit for Scholar / Writer / Clew models (postgres-per-user purpose).

Shared-postgres model (the GitHub way): one database, tenant isolation at the
row level. Every user-data table must carry a user-or-project ownership path so
no queryset can leak across tenants. Reference/global tables (journals, topics,
arxiv categories) are explicitly exempt.

Two layers:
1. Static audit — every models.Model subclass in the three apps either has a
   direct user/owner/project FK or is on the EXEMPT list with a reason.
2. Dynamic isolation — user A's rows are invisible to user B through the ORM.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.security]

APPS = ("scholar_app", "writer_app", "clew_app")

# Model label -> reason it carries no tenant ownership.
EXEMPT = {
    # Scholar reference data: global bibliographic entities, no tenant content.
    "scholar_app.Author": "global reference",
    "scholar_app.Journal": "global reference",
    "scholar_app.Topic": "global reference",
    "scholar_app.AuthorPaper": "global reference join",
    "scholar_app.Citation": "global citation graph edge",
    "scholar_app.SearchIndex": "global index row",
    # Writer reference data.
    "writer_app.ArxivCategory": "global arxiv taxonomy",
    # Scholar global registries (no tenant rows).
    "scholar_app.Repository": "global repository registry",
    "scholar_app.SearchFilter": "global filter definitions",
}


def _tenant_models():
    from django.apps import apps as dj_apps

    found = {}
    for app_label in APPS:
        try:
            app = dj_apps.get_app_config(app_label)
        except LookupError:
            continue
        for model in app.get_models():
            found[f"{app_label}.{model.__name__}"] = model
    return found


def _ownership_field(model, _depth=0):
    """Ownership field name, direct or one hop via a parent, or None.

    Child rows (Figure -> Manuscript -> owner/project) are tenant-owned
    through their parent chain; only one hop is followed to keep the audit
    strict — deeper chains must be justified explicitly.
    """
    if _depth > 1:
        return None
    for f in model._meta.get_fields():
        if not (getattr(f, "many_to_one", False) or getattr(f, "one_to_one", False)):
            continue
        if f.name in ("user", "owner", "project"):
            return f.name
        target = getattr(f.remote_field, "model", None)
        tname = getattr(target, "__name__", "")
        if tname in ("User", "Project"):
            return f.name
        if target is not None and _depth == 0:
            parent_chain = _ownership_field(target, _depth + 1)
            if parent_chain is not None:
                return f"{f.name} -> {parent_chain}"
    return None


def test_every_model_has_ownership_or_exemption():
    """No orphan tables: static gate against tenant-less user-data models."""
    missing = []
    for label, model in sorted(_tenant_models().items()):
        if _ownership_field(model) is None and label not in EXEMPT:
            missing.append(label)
    assert not missing, (
        "models without user/owner/project ownership and no exemption: "
        + ", ".join(missing)
    )


def test_exemptions_still_exist():
    """Exemption list must not go stale (typo'd label = silent hole)."""
    models = _tenant_models()
    stale = [label for label in EXEMPT if label not in models]
    assert not stale, f"stale exemptions (model gone/renamed): {stale}"


def _make_users():
    from django.contrib.auth import get_user_model

    User = get_user_model()
    a = User.objects.create_user(username="owner_a_0925", password="x")
    b = User.objects.create_user(username="owner_b_0925", password="x")
    return a, b


@pytest.mark.django_db
def test_saved_search_isolation():
    """User B cannot see user A's saved searches through the ORM."""
    from apps.workspace.scholar_app.models.search.models import SavedSearch

    a, b = _make_users()
    SavedSearch.objects.create(user=a, name="a-search", query_text="graphene")
    assert SavedSearch.objects.filter(user=a).count() == 1
    assert SavedSearch.objects.filter(user=b).count() == 0
    assert SavedSearch.objects.exclude(user=b).filter(name="a-search").count() == 1


@pytest.mark.django_db
def test_clew_registration_isolation():
    """Clew hash registrations are per-user (unique_together enforces it)."""
    from apps.workspace.clew_app.models import HashRegistration

    a, b = _make_users()
    HashRegistration.objects.create(user=a, hash="a" * 64)
    assert HashRegistration.objects.filter(user=a).count() == 1
    assert HashRegistration.objects.filter(user=b).count() == 0


def test_no_sqlite_references_in_settings():
    """No settings module may point at sqlite — postgres everywhere."""
    from pathlib import Path

    base = Path(__file__).resolve().parents[2]
    hits = []
    for settings_file in (base / "config" / "settings").glob("settings*.py"):
        text = settings_file.read_text()
        if "sqlite" in text.lower():
            hits.append(settings_file.name)
    assert not hits, f"sqlite references in settings: {hits}"
