"""The required SDK must preserve the UI contracts used by mounted apps.

Distribution identity and installed behavior are independent: a correct SDK
floor cannot prove that panes reach templates or that palette imports contain
their tokens. The delivery controls below continue to exercise those contracts,
including refusal of unknown panes and recursive CSS imports.
"""
from __future__ import annotations

import re
import tomllib
from importlib.util import find_spec
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

REPO = Path(__file__).resolve().parents[2]
DECLARED_FLOOR = Version("0.3.0")
UNKNOWN_PANE = "not-a-real-pane"


@pytest.fixture(name="sdk_requirement")
def _sdk_requirement() -> Requirement:
    project = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]
    required = [Requirement(raw) for raw in project["dependencies"]]
    sdk = [req for req in required if req.name == "scitex-sdk"]
    assert len(sdk) == 1, "shared runtime must declare one base SDK dependency"
    return sdk[0]


def test_required_sdk_excludes_published_facade_versions(sdk_requirement):
    assert not sdk_requirement.specifier.contains(Version("0.2.0"))
    assert not sdk_requirement.specifier.contains(Version("0.2.1"))


def test_required_sdk_admits_the_consolidated_version(sdk_requirement):
    assert sdk_requirement.specifier.contains(DECLARED_FLOOR)


def test_no_dependency_group_requires_independent_app_or_ui():
    project = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]
    groups = {"dependencies": project["dependencies"]}
    groups.update(project.get("optional-dependencies", {}))
    peers = [
        (group, raw)
        for group, raws in groups.items()
        for raw in raws
        if Requirement(raw).name in {"scitex-app", "scitex-ui"}
    ]
    assert peers == []


def _resolve_css(path: Path, _seen: frozenset[Path] = frozenset()) -> str:
    """Read a stylesheet with its ``@import``s inlined, as a browser would.

    Necessary rather than convenient. scitex-ui 0.16.0 split
    ``primitives/colors.css`` into a 22-line BARREL that ``@import``s
    ``colors/_light.css`` and ``colors/_dark.css``; a single-file read of that
    path therefore finds no tokens at all and looks identical to a release that
    lost them. That false alarm was raised for real on 2026-08-18 before the
    barrel was noticed, which is why this walks the graph instead.

    Cycles are guarded because a self-referential import would otherwise recurse
    until the interpreter stops us, turning a stylesheet typo into a crash in
    the test suite rather than a finding.
    """
    if path in _seen or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    seen = _seen | {path}
    for ref in re.findall(r"""@import\s+(?:url\()?["']([^"']+)["']\)?""", text):
        text += _resolve_css((path.parent / ref).resolve(), seen)
    return text


@pytest.fixture(name="installed_primitives")
def _installed_primitives() -> tuple[Path, str]:
    """The installed scitex-ui's primitives layer, ``@import``s inlined.

    Shared by the two tests below so they read the SAME bytes: one asserts the
    read happened, the other asserts what it contains. Splitting them is what
    makes a red run say which of those two things went wrong.
    """
    from scitex_sdk import ui

    colors = ui.get_static_dir() / "css/primitives/colors.css"
    return colors, _resolve_css(colors)


def test_installed_primitives_read_reaches_a_populated_stylesheet(
    installed_primitives: tuple[Path, str],
) -> None:
    # Arrange — the POSITIVE CONTROL for the test below, and it is separate
    # rather than a second assert precisely so a failure names which half broke.
    # An empty read -- wrong path, moved file, or a barrel whose tokens live in
    # children -- is indistinguishable from a genuine missing token, and all
    # THREE of those produced a wrong zero against this exact package on
    # 2026-08-18. Without this control, that ambiguity lands on whoever reads CI.
    colors, css = installed_primitives

    # Act
    control = re.findall(r"--text-primary\s*:", css)

    # Assert
    assert control, (
        f"positive control failed: '--text-primary' is not defined anywhere "
        f"reachable from {colors}. THE READ IS WRONG, NOT THE PACKAGE -- check "
        f"the path exists and that @imports were followed. Do not interpret "
        f"this as a missing token."
    )


def test_installed_primitives_actually_define_the_link_token(
    installed_primitives: tuple[Path, str],
) -> None:
    # Arrange — the DELIVERY half of the token contract, and the half this file
    # was missing entirely. The floor tests above assert the PROMISE in
    # pyproject.toml; nothing asserted that the scitex-ui actually present here
    # defines the token. Two independent facts, for the reason the module
    # docstring already gives for panes: the mounted apps are installed editable,
    # so the declared floor never participates in resolution.
    colors, css = installed_primitives

    # Act
    declarations = re.findall(r"--text-link\s*:\s*([^;]+);", css)

    # Assert
    assert declarations, (
        f"the installed scitex-ui does not define '--text-link' in its "
        f"primitives layer (read from {colors}, @imports followed; the control "
        f"test above passing means the read is sound). Hub @imports this layer, "
        f"so var(--text-link) resolves to nothing and link colour sits at "
        f"2.36:1 against a 4.5:1 AA requirement -- silently, with no 404 and no "
        f"exception. Install scitex-sdk>={DECLARED_FLOOR}."
    )


def test_installed_shell_context_accepts_the_pane_declaration() -> None:
    # Arrange — exercise the real call the request path makes, not the
    # signature. inspect.signature() would also pass on a **kwargs sink.
    from scitex_sdk.ui.branding import shell_context

    declaration = {"ai": "unused", "files": "unused", "viewer": "unused"}

    # Act
    context = shell_context("Storage", panes=declaration)

    # Assert — accepted AND carried into the template context, because
    # accepting an argument and dropping it look identical from the caller.
    assert context["panes"] == declaration


def test_installed_shell_context_rejects_an_unknown_pane() -> None:
    # Arrange — POSITIVE CONTROL. See this module's docstring: without it,
    # a **kwargs signature that discards `panes` satisfies the test above.
    from scitex_sdk.ui.branding import shell_context

    # Act — an unknown pane must fail loudly at the call site, so the call
    # itself is the thing under test and is made inside the expectation.
    def call_with_unknown_pane() -> None:
        shell_context("Storage", panes={UNKNOWN_PANE: "unused"})

    # Assert
    with pytest.raises(ValueError):
        call_with_unknown_pane()


@pytest.mark.skipif(
    find_spec("scitex_storage") is None,
    reason="scitex-storage not installed (optional mount)",
)
def test_installed_scitex_ui_honours_the_mounted_apps_declaration() -> None:
    # Arrange — end to end, with the declaration the mounted app actually
    # ships rather than a copy of it restated here. A copy would assert that
    # this file agrees with itself while storage was free to change.
    from scitex_storage._django import views
    from scitex_sdk.ui.branding import shell_context

    declaration = views.SHELL_PANES

    # Act
    context = shell_context("Storage", panes=declaration)

    # Assert
    assert context["panes"] == declaration
