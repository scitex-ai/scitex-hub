#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/demo_videos: stale-selector and UI-contract detection."""

import sys
from pathlib import Path

import pytest

DEMO_VIDEOS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo_videos"
sys.path.insert(0, str(DEMO_VIDEOS_DIR))

from demo_scenario import parse_scenario  # noqa: E402
from demo_selectors import (  # noqa: E402
    SelectorContract,
    SourceIndex,
    check_contracts,
    check_scenario,
    contract_fingerprint,
    is_semantic,
    locate_selector,
    missing_scenario_selectors,
    selector_tokens,
    stale_against_manifest,
)

SCENARIO = {
    "app": "demo",
    "title": {"en": "A demo"},
    "languages": ["en"],
    "steps": [
        {"action": "goto", "value": "/apps/"},
        {"action": "type", "selector": "#name", "value": "x"},
        {"action": "click", "selector": '[data-path="README.md"]'},
    ],
}


def write_template(root: Path, relative: str, body: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_selector_tokens_require_the_id_literal_and_the_data_attribute():
    # Arrange / Act / Assert
    assert selector_tokens("#name") == ['id="name"']
    # A data attribute is rendered from a value, so only its presence is checked.
    assert selector_tokens('[data-path="README.md"]') == ["data-path="]


def test_is_semantic_accepts_ids_and_data_attributes_only():
    # Arrange / Act / Assert
    assert is_semantic("#create-submit-btn")
    assert is_semantic('[data-path="README.md"]')
    assert not is_semantic("text=README.md")
    assert not is_semantic(".monaco-editor .view-lines")


def test_check_contracts_passes_when_the_owner_file_has_the_token(tmp_path):
    # Arrange
    write_template(tmp_path, "templates/part.html", '<button id="trigger"></button>')
    contracts = (SelectorContract("trigger", "#trigger", "templates/part.html",
                                  'id="trigger"', "1"),)
    # Act
    statuses = check_contracts(tmp_path, contracts)
    # Assert
    assert [(status.name, status.ok) for status in statuses] == [("trigger", True)]


def test_a_moved_control_is_reported_as_stale_with_its_owner(tmp_path):
    # Arrange: the control is gone from the file that used to define it.
    write_template(tmp_path, "templates/part.html", "<button></button>")
    contracts = (SelectorContract("trigger", "#trigger", "templates/part.html",
                                  'id="trigger"', "1"),)
    index = SourceIndex(tmp_path, {"templates/part.html": "<button></button>"})
    # Act
    found = index.locate("#trigger")
    statuses = check_contracts(tmp_path, contracts)
    # Assert
    assert found == []
    assert [(status.name, status.ok, status.reason) for status in statuses] == [
        ("trigger", False, "'id=\"trigger\"' is not in the owner file")
    ]


def test_a_gone_owner_file_is_reported_as_stale(tmp_path):
    # Arrange
    contracts = (SelectorContract("trigger", "#trigger", "templates/gone.html",
                                  'id="trigger"', "1"),)
    # Act
    statuses = check_contracts(tmp_path, contracts)
    # Assert
    assert [status.reason for status in statuses] == ["owner file is gone"]


def test_locate_selector_finds_the_file_that_defines_a_data_attribute(tmp_path):
    # Arrange
    write_template(tmp_path, "apps/infra/project_app/templates/tree.html",
                   '<div class="wft-file" data-path="{{ file.path }}"></div>')
    # Act
    found = locate_selector(tmp_path, '[data-path="README.md"]')
    # Assert
    assert found == ["apps/infra/project_app/templates/tree.html"]


def test_check_scenario_marks_missing_and_fragile_selectors(tmp_path):
    # Arrange
    write_template(tmp_path, "apps/infra/project_app/templates/create.html",
                   '<input id="name" /><button id="create-submit-btn"></button>')
    write_template(tmp_path, "apps/infra/project_app/templates/tree.html",
                   '<div data-path="{{ file.path }}"></div>')
    scenario = parse_scenario(SCENARIO)
    # Act
    report = check_scenario(tmp_path, scenario)
    # Assert
    assert missing_scenario_selectors(report) == []
    assert [entry["selector"] for entry in report["selectors"]] == [
        "#name", '[data-path="README.md"]'
    ]
    assert all(entry["semantic"] for entry in report["selectors"])


def test_check_scenario_reports_a_fragile_text_selector(tmp_path):
    # Arrange
    write_template(tmp_path, "apps/infra/project_app/templates/create.html", "<div></div>")
    scenario = parse_scenario({
        "app": "demo",
        "title": {"en": "A demo"},
        "languages": ["en"],
        "steps": [{"action": "click", "selector": "text=README.md"}],
    })
    # Act
    report = check_scenario(tmp_path, scenario)
    # Assert
    assert missing_scenario_selectors(report) == ["text=README.md"]
    assert [entry["semantic"] for entry in report["selectors"]] == [False]


def test_contract_fingerprint_changes_when_a_contract_version_moves():
    # Arrange
    base = (SelectorContract("a", "#a", "f.html", 'id="a"', "1"),)
    bumped = (SelectorContract("a", "#a", "f.html", 'id="a"', "2"),)
    # Act / Assert
    assert contract_fingerprint(base) == contract_fingerprint(base)
    assert contract_fingerprint(base) != contract_fingerprint(bumped)


def test_stale_against_manifest_flags_a_changed_contract_set(tmp_path):
    # Arrange: the manifest was recorded against a different contract set.
    write_template(tmp_path, "templates/global_base_partials/language_switcher.html",
                   '<button id="lang-select-trigger"></button>')
    manifest = {"ui_contract": {"fingerprint": "0" * 64, "contracts": {}}}
    # Act
    verdict = stale_against_manifest(manifest, tmp_path)
    # Assert
    assert verdict["stale"] is True
    assert verdict["recorded_fingerprint"] == "0" * 64
    assert verdict["current_fingerprint"] == contract_fingerprint()


def test_stale_against_manifest_accepts_the_current_contract_set(tmp_path):
    # Arrange: every owner file carries all of its contracts' tokens, so a
    # checkout in good order reports no staleness for a manifest recorded from it.
    from demo_selectors import SELECTOR_CONTRACTS

    by_owner: dict[str, list[str]] = {}
    for contract in SELECTOR_CONTRACTS:
        by_owner.setdefault(contract.owner, []).append(contract.token)
    for owner, tokens in by_owner.items():
        write_template(tmp_path, owner, "\n".join(tokens))
    manifest = {
        "ui_contract": {
            "fingerprint": contract_fingerprint(),
            "contracts": {contract.name: contract.version for contract in SELECTOR_CONTRACTS},
        }
    }
    # Act
    verdict = stale_against_manifest(manifest, tmp_path)
    # Assert
    assert verdict["stale"] is False
    assert verdict["broken_contracts"] == []


@pytest.mark.parametrize("selector", ["#a", "[data-x]", '[data-x="1"]'])
def test_semantic_selectors_have_tokens(selector):
    # Arrange / Act / Assert
    assert selector_tokens(selector)
