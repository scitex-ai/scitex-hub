"""Leaf metadata must not silently collide in the assistant's app map."""

from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from django.test import override_settings
from django.urls import include, path

from apps.infra.llm_app.apps import LlmAppConfig
from apps.infra.llm_app.skills import registry

urlpatterns = [
    path(
        "apps/synthetic/",
        include(
            (
                [path("", lambda request: HttpResponse("leaf"), name="index")],
                "synthetic",
            )
        ),
    )
]


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    monkeypatch.setattr(registry, "_registry", {})
    monkeypatch.setattr(registry, "_registry_source", {})


def leaf(name, app_name="synthetic"):
    return SimpleNamespace(
        name=name,
        manifest={
            "agent_skill": {
                "app_name": app_name,
                "display_name": "Synthetic",
                "description": "Leaf-owned capability metadata",
                "url_route": "synthetic:index",
            }
        },
    )


def test_metadata_registers_without_leaf_importing_hub_and_resolves_live_mount():
    config = leaf("synthetic_leaf._django")
    LlmAppConfig._register_manifest_skill(config)
    LlmAppConfig._register_manifest_skill(config)  # Same owner may reload.
    assert registry.get_skill_source("synthetic") == "synthetic_leaf._django.manifest"
    with override_settings(ROOT_URLCONF=__name__):
        assert registry.get_skill("synthetic").resolve_url() == "/apps/synthetic/"


def test_two_leaf_manifests_cannot_silently_claim_one_app_name():
    LlmAppConfig._register_manifest_skill(leaf("first_leaf._django"))
    with pytest.raises(registry.DuplicateSkillError):
        LlmAppConfig._register_manifest_skill(leaf("second_leaf._django"))
    assert registry.get_skill_source("synthetic") == "first_leaf._django.manifest"


def test_same_leaf_legacy_skill_is_preserved_and_other_leaf_is_rejected():
    legacy = registry.Skill("synthetic", "Legacy", "Explicit legacy capability")
    registry.register(legacy, source="first_leaf._django.skill")
    LlmAppConfig._register_manifest_skill(leaf("first_leaf._django"))
    assert registry.get_skill("synthetic") is legacy
    with pytest.raises(registry.DuplicateSkillError):
        LlmAppConfig._register_manifest_skill(leaf("second_leaf._django"))


def test_invalid_leaf_metadata_is_not_silently_dropped():
    with pytest.raises(ValueError, match="agent_skill must be an object"):
        LlmAppConfig._register_manifest_skill(
            SimpleNamespace(name="invalid", manifest={"agent_skill": []})
        )
