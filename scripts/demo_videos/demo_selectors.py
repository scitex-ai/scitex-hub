"""Stale-selector and UI-contract detection for the demo-video pipeline.

A scenario locates controls in the real UI. When Hub or a leaf app renames an id,
moves a button into another template, or drops a control, the recording does not
fail loudly — Playwright times out mid-flow, or a caption ends up describing a
screen that no longer exists, and the published video silently drifts away from
the product. The spec (docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md section 8) asks
for exactly two things: stable ids/data attributes instead of translated labels,
and detection of missing selectors and visual drift before publishing.

This module is the detector:

* ``SELECTOR_CONTRACTS`` names the controls the pipeline depends on and the file
  that must define each one, so a rename is caught in CI without a browser;
* ``locate_selector`` searches the checkout for a scenario's selector, so a
  scenario written for a control that no longer exists is caught before a render;
* ``contract_fingerprint`` is recorded in the render manifest, so a published
  video can be marked stale when the contract set it was recorded against moves.

Selectors that are not ids or data attributes (``text=README.md``) are reported
as fragile rather than fatal: they work today, but the spec's rule is that
translated labels never locate a control.
"""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SOURCE_GLOBS = (
    "apps/**/templates/**/*.html",
    "templates/**/*.html",
    "apps/**/static/**/*.ts",
    "apps/**/static/**/*.js",
    "apps/**/static/**/*.html",
    "static/**/*.ts",
    "static/**/*.js",
    "templates/**/*.js",
    "src/**/*.py",
)
# Selector shapes the spec allows: an id, a data attribute, or a class on a
# semantic element. A `text=` selector follows a translated label and is fragile.
SEMANTIC_PREFIXES = ("#", "[data-", "*[data-")
#: Any `#id` anywhere in a selector, not only at the start: `#form textarea[name=q]`
#: is a compound selector, and the id inside it is the stable half worth checking.
ID_ANYWHERE = re.compile(r"#([A-Za-z0-9_-]+)")
#: A bracketed attribute: `[data-path="x"]`, `[data-paper-id]`, `[name=q]`.
ATTRIBUTE_ANYWHERE = re.compile(r"\[\s*([a-zA-Z0-9_-]+)\s*(?:[~|^$*]?=\s*([^\]]*))?\s*\]")


@dataclass(frozen=True)
class SelectorContract:
    """One control the video pipeline depends on."""

    name: str
    selector: str
    owner: str
    token: str
    version: str
    note: str = ""


@dataclass(frozen=True)
class ContractStatus:
    name: str
    selector: str
    version: str
    owner: str
    ok: bool
    reason: str = ""


# The controls the scenarios and the recorder itself drive. `token` is the text
# that must exist in `owner`; bump `version` when the control changes in a way
# that invalidates a recording (moved, relabelled, replaced by another control).
SELECTOR_CONTRACTS: tuple[SelectorContract, ...] = (
    SelectorContract(
        name="figrecipe-app-mount",
        selector='#app-mount[data-app-slug="figrecipe"][data-embedded="true"]',
        owner="apps/workspace/figrecipe_app/templates/figrecipe_app/figrecipe_partial.html",
        token='data-app-slug="figrecipe"',
        version="1",
        note="The hub's FigRecipe surface is the app-editor shell; the inner plot and "
             "data controls arrive over the vite bridge and are not in this checkout, "
             "so this mount is the only hook a scenario can assert for that app.",
    ),
    SelectorContract(
        name="language-switcher-trigger",
        selector="#lang-select-trigger",
        owner="templates/global_base_partials/language_switcher.html",
        token='id="lang-select-trigger"',
        version="1",
        note="The recorder switches the UI locale through the site's own switcher.",
    ),
    SelectorContract(
        name="language-switcher-fields",
        selector="form.lang-select-item input[name=language]",
        owner="templates/global_base_partials/language_switcher.html",
        token='name="language"',
        version="1",
        note="One POST per language; the value is the Django locale code.",
    ),
    SelectorContract(
        name="sign-in-username",
        selector="#username",
        owner="apps/infra/auth_app/templates/auth_app/signin.html",
        token='id="username"',
        version="1",
    ),
    SelectorContract(
        name="sign-in-password",
        selector="#password",
        owner="apps/infra/auth_app/templates/auth_app/signin.html",
        token='id="password"',
        version="1",
    ),
    SelectorContract(
        name="sign-in-submit",
        selector="#login-form button[type=submit]",
        owner="apps/infra/auth_app/templates/auth_app/signin.html",
        token='id="login-form"',
        version="1",
    ),
    SelectorContract(
        name="project-name",
        selector="#name",
        owner="apps/infra/project_app/templates/project_app/projects/create_partials/create_name_field.html",
        token='id="name"',
        version="1",
        note="Shared by every create tab, so it survives the tab redesign.",
    ),
    SelectorContract(
        name="project-description",
        selector="#description",
        owner="apps/infra/project_app/templates/project_app/projects/create.html",
        token='id="description"',
        version="1",
    ),
    SelectorContract(
        name="project-create-submit",
        selector="#create-submit-btn",
        owner="apps/infra/project_app/templates/project_app/projects/create.html",
        token='id="create-submit-btn"',
        version="1",
    ),
    SelectorContract(
        name="project-tree-file-row",
        selector='[data-path="README.md"]',
        owner="static/shared/ts/components/workspace-files-tree/_TreeRenderer.ts",
        token="data-path=",
        version="1",
        note="The default project screen is the Explorer/Finder tree; the row carries "
             "the file path as a data attribute, so a file is opened by path and not by "
             "its (translatable) label. The GitHub-style browser renders the same attribute.",
    ),
    SelectorContract(
        name="writer-section-selector-toggle",
        selector="#section-selector-toggle",
        owner="apps/workspace/writer_app/templates/writer_app/index_partials/main_editor.html",
        token='id="section-selector-toggle"',
        version="1",
    ),
    SelectorContract(
        name="writer-preview-log-section",
        selector="[data-section=preview-log] .details-section__header",
        owner="apps/workspace/writer_app/templates/writer_app/index_partials/details_panel.html",
        token='data-section="preview-log"',
        version="1",
    ),
    SelectorContract(
        name="writer-preview-compile",
        selector="#details-preview-compile-btn",
        owner="apps/workspace/writer_app/templates/writer_app/index_partials/details_panel.html",
        token='id="details-preview-compile-btn"',
        version="1",
    ),
    SelectorContract(
        name="writer-download-toolbar",
        selector="#download-btn-toolbar",
        owner="apps/workspace/writer_app/templates/writer_app/index_partials/main_editor.html",
        token='id="download-btn-toolbar"',
        version="1",
    ),
    SelectorContract(
        name="demo-player-speed-control",
        selector='[data-speed="2"]',
        owner="apps/infra/public_app/templates/public_app/pages/video_player.html",
        token="data-speed=",
        version="1",
        note="The speed buttons are addressed by their rate, never by their label.",
    ),
    SelectorContract(
        name="demo-player-language-control",
        selector="button[data-demo-lang]",
        owner="apps/infra/public_app/templates/public_app/pages/video_player.html",
        token="data-demo-lang=",
        version="1",
        note="The position-preserving language switch binds these controls; renaming the "
             "attribute makes every published manifest stale on purpose.",
    ),
    SelectorContract(
        name="scholar-search-form",
        selector="#literatureSearchForm textarea[name=q]",
        owner="apps/workspace/scholar_app/templates/scholar_app/search_partials/search.html",
        token='id="literatureSearchForm"',
        version="1",
        note="Form-scoped: the textarea itself carries no id, so the form's id plus the "
             "untranslated name attribute is the stable half. A textarea id would be better.",
    ),
    SelectorContract(
        name="scholar-search-submit",
        selector="#searchButton",
        owner="apps/workspace/scholar_app/templates/scholar_app/search_partials/search.html",
        token='id="searchButton"',
        version="1",
    ),
    SelectorContract(
        name="scholar-result-container",
        selector="#scitex-results-container .save-btn",
        owner="apps/workspace/scholar_app/templates/scholar_app/search_partials/search.html",
        token='id="scitex-results-container"',
        version="1",
        note="The per-result save control is generated by search/_result-card.ts as "
             "`.save-btn` with no id and no data attribute; the selector is anchored on the "
             "container id, and scitex-scholar should give the button a stable hook.",
    ),
    SelectorContract(
        name="scholar-library-tab",
        selector="#tab-library",
        owner="apps/workspace/scholar_app/templates/scholar_app/scholar_unified.html",
        token='id="tab-library"',
        version="1",
    ),
    SelectorContract(
        name="scholar-library-paper",
        selector="#library-papers-list .library-paper-card[data-paper-id]",
        owner="apps/workspace/scholar_app/templates/scholar_app/library_partials/library_main.html",
        token='id="library-papers-list"',
        version="1",
        note="The saved-paper card carries data-paper-id (a value only known at runtime), "
             "so the library's list id plus the attribute's presence is what is checked.",
    ),
)
CONTRACTS_BY_SELECTOR = {contract.selector: contract for contract in SELECTOR_CONTRACTS}

# Selectors whose owner is not in this checkout, so a static sweep cannot confirm
# them. They are listed with the reason and verified against the live DOM at
# record time; a scenario that acquires a new one of these shows up as a change
# to this table, which is the point of writing them down.
UNVERIFIABLE_SELECTORS = {
    ".monaco-editor .view-lines": "Monaco's own DOM, owned by the editor library; "
                                  "scitex-writer should expose a stable editor id",
    ".monaco-editor textarea": "Monaco's own DOM, owned by the editor library; "
                               "scitex-writer should expose a stable editor id",
}


def contract_fingerprint(contracts=SELECTOR_CONTRACTS) -> str:
    """A digest of the contract set, recorded in the manifest for stale detection."""
    payload = json.dumps(
        sorted(
            [contract.name, contract.selector, contract.version, contract.owner, contract.token]
            for contract in contracts
        ),
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check_contracts(repo_root: Path, contracts=SELECTOR_CONTRACTS) -> list[ContractStatus]:
    """Verify every contract's token still exists in the file that must define it."""
    repo_root = Path(repo_root)
    statuses = []
    for contract in contracts:
        owner_path = repo_root / contract.owner
        if not owner_path.exists():
            statuses.append(
                ContractStatus(contract.name, contract.selector, contract.version,
                               contract.owner, False, "owner file is gone")
            )
            continue
        if contract.token not in owner_path.read_text(encoding="utf-8", errors="replace"):
            statuses.append(
                ContractStatus(contract.name, contract.selector, contract.version,
                               contract.owner, False, f"{contract.token!r} is not in the owner file")
            )
            continue
        statuses.append(
            ContractStatus(contract.name, contract.selector, contract.version, contract.owner, True)
        )
    return statuses


def source_files(repo_root: Path) -> list[Path]:
    root = Path(repo_root)
    seen, files = set(), []
    for pattern in SOURCE_GLOBS:
        for path in root.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                files.append(path)
    return sorted(files)


class SourceIndex:
    """Every candidate source file read once, so a selector sweep is one pass.

    The demo-video checkout is a few thousand templates and scripts; reading them
    per selector turned the check into 35k file reads and a two-minute wait. The
    scenarios only need a token search, so the text is loaded once and reused.
    """

    def __init__(self, repo_root: Path, texts: dict[str, str]):
        self.repo_root = Path(repo_root)
        self.texts = texts

    @classmethod
    def build(cls, repo_root: Path) -> "SourceIndex":
        repo_root = Path(repo_root)
        texts = {}
        for path in source_files(repo_root):
            texts[str(path.relative_to(repo_root))] = path.read_text(
                encoding="utf-8", errors="replace"
            )
        return cls(repo_root, texts)

    def locate(self, selector: str) -> list[str]:
        tokens = selector_tokens(selector)
        if not tokens:
            return []
        return sorted(
            relative for relative, text in self.texts.items()
            if all(token in text for token in tokens)
        )


def selector_tokens(selector: str) -> list[str]:
    """The literals a source file must contain for `selector` to match its DOM.

    A selector may be compound — `#form textarea[name=q]`, `#list .card[data-id]` — so
    every id and every bracketed attribute in it is checked, not just a leading one.
    An id is written literally in a template or a script; a `data-` attribute is
    rendered from a value (`data-path="{{ file.path }}"`) or built in JS, so only the
    attribute itself is required to exist. Other attributes (`name=q`) are checked for
    presence too, which is what makes a form-scoped selector verifiable.
    """
    tokens = []
    for name in ID_ANYWHERE.findall(selector):
        token = f'id="{name}"'
        if token not in tokens:
            tokens.append(token)
    for name, value in ATTRIBUTE_ANYWHERE.findall(selector):
        cleaned = (value or "").strip().strip("'\"")
        if name.startswith("data-"):
            token = f"{name}="
        elif cleaned and "{{" not in cleaned and "{%" not in cleaned:
            token = f'{name}="{cleaned}"'
        else:
            token = f"{name}="
        if token not in tokens:
            tokens.append(token)
    return tokens


def is_semantic(selector: str) -> bool:
    """Whether the selector anchors on an id or a data attribute, per the spec."""
    selector = selector.strip()
    if ID_ANYWHERE.search(selector) or "[data-" in selector:
        return True
    return any(selector.startswith(prefix) for prefix in SEMANTIC_PREFIXES)


def locate_selector(repo_root: Path, selector: str, files: list[Path] | None = None) -> list[str]:
    """Repo-relative files that define `selector`; empty means the control is gone."""
    tokens = selector_tokens(selector)
    if not tokens:
        return []
    if files is None:
        return SourceIndex.build(repo_root).locate(selector)
    found = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if all(token in text for token in tokens):
            found.append(str(path.relative_to(repo_root)))
    return found


def scenario_selectors(scenario) -> list[str]:
    """Every selector a scenario needs, in step order, without duplicates."""
    selectors = []
    for step in scenario.steps:
        for selector in step.selector.values():
            if selector and selector not in selectors:
                selectors.append(selector)
    return selectors


def check_scenario(repo_root: Path, scenario, index: SourceIndex | None = None) -> dict:
    """Per-selector verdict for one scenario: contract, owner files, semantic shape."""
    index = index or SourceIndex.build(repo_root)
    entries = []
    for selector in scenario_selectors(scenario):
        contract = CONTRACTS_BY_SELECTOR.get(selector)
        owners = index.locate(selector)
        unverifiable = UNVERIFIABLE_SELECTORS.get(selector, "")
        entries.append(
            {
                "selector": selector,
                "semantic": is_semantic(selector),
                "contract": contract.name if contract else "",
                "contract_version": contract.version if contract else "",
                "found_in": owners,
                "static_check": "unverifiable" if unverifiable else "checked",
                "note": unverifiable,
                # An unverifiable selector is not a pass: it is a selector whose
                # owner lives outside this checkout, so the live check is the
                # only thing that can confirm it. It is reported, not hidden.
                "ok": bool(owners) or bool(unverifiable),
            }
        )
    return {"app": scenario.app, "selectors": entries}


def missing_scenario_selectors(report: dict) -> list[str]:
    return [entry["selector"] for entry in report["selectors"] if not entry["ok"]]


def fragile_scenario_selectors(report: dict) -> list[str]:
    return [entry["selector"] for entry in report["selectors"] if not entry["semantic"]]


def unverifiable_scenario_selectors(report: dict) -> list[str]:
    return [
        entry["selector"] for entry in report["selectors"]
        if entry.get("static_check") == "unverifiable"
    ]


def stale_against_manifest(manifest: dict, repo_root: Path) -> dict:
    """Compare a published render's contract set with the checkout as it is now."""
    recorded = (manifest.get("ui_contract") or {}).get("fingerprint", "")
    current = contract_fingerprint()
    statuses = check_contracts(repo_root)
    broken = [asdict(status) for status in statuses if not status.ok]
    changed = [
        asdict(status) for status in statuses
        if (manifest.get("ui_contract") or {}).get("contracts", {}).get(status.name) not in (None, status.version)
    ]
    return {
        "recorded_fingerprint": recorded,
        "current_fingerprint": current,
        "stale": bool(recorded and recorded != current) or bool(broken),
        "broken_contracts": broken,
        "changed_contracts": changed,
    }


def check_live(page, scenario, timeout_ms: int = 5_000) -> list[dict]:
    """Resolve each scenario selector on a live page; report what the UI no longer has."""
    results = []
    for step_index, step in enumerate(scenario.steps, 1):
        for language, selector in step.selector.items():
            if not selector:
                continue
            try:
                page.wait_for_selector(selector, timeout=timeout_ms)
                count = page.locator(selector).count()
            except Exception as error:  # Playwright raises its own timeout class
                results.append(
                    {"step": step_index, "language": language, "selector": selector,
                     "count": 0, "ok": False, "error": type(error).__name__}
                )
                continue
            results.append(
                {"step": step_index, "language": language, "selector": selector,
                 "count": count, "ok": True, "error": ""}
            )
    return results


@dataclass(frozen=True)
class LiveCheck:
    """A page that can be visited signed out, and the contracts it must satisfy."""

    path: str
    contracts: tuple[str, ...]
    note: str = ""


# The controls that exist on a signed-out page. Everything else (create form, file
# tree, Writer) needs the demo account, so the live check says so instead of
# reporting a false failure; record.py checks those by resolving them for real
# during a render.
LIVE_CHECKS: tuple[LiveCheck, ...] = (
    LiveCheck(
        path="/auth/signin/",
        contracts=("sign-in-username", "sign-in-password", "sign-in-submit"),
    ),
    LiveCheck(
        path="/demos/",
        contracts=("language-switcher-trigger", "language-switcher-fields"),
        note="The footer language switcher is how every rendition picks its UI language.",
    ),
)
SIGNED_IN_PATHS = ("/new/", "/{username}/", "/apps/writer/")


def contracts_by_name() -> dict[str, SelectorContract]:
    return {contract.name: contract for contract in SELECTOR_CONTRACTS}


def run_live_checks(base_url: str, timeout_ms: int = 5_000, checks=LIVE_CHECKS) -> list[dict]:
    """Visit each signed-out page and resolve the contracts it must satisfy."""
    from playwright.sync_api import sync_playwright

    known = contracts_by_name()
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        for check in checks:
            page.goto(f"{base_url.rstrip('/')}{check.path}", wait_until="domcontentloaded",
                      timeout=60_000)
            for name in check.contracts:
                contract = known.get(name)
                if contract is None:
                    results.append({"page": check.path, "contract": name, "selector": "",
                                    "count": 0, "ok": False, "error": "unknown contract"})
                    continue
                try:
                    # `state="attached"`, not the default "visible": the language
                    # menu lives in the DOM with display:none until the trigger is
                    # clicked, and a hidden-but-present control is exactly what the
                    # recorder clicks after opening it.
                    page.wait_for_selector(contract.selector, state="attached", timeout=timeout_ms)
                    locator = page.locator(contract.selector)
                    count, visible = locator.count(), 0
                    for index in range(count):
                        if locator.nth(index).is_visible():
                            visible += 1
                    error = ""
                except Exception as exception:  # Playwright's own timeout class
                    count, visible, error = 0, 0, type(exception).__name__
                results.append({"page": check.path, "contract": name,
                                "selector": contract.selector, "count": count,
                                "visible": visible,
                                "ok": count > 0, "error": error, "note": check.note})
        context.close()
        browser.close()
    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check demo-video selectors and UI contracts")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--scenario", type=Path, action="append", default=None,
                        help="scenario YAML to check (repeatable; default: every scenario)")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--strict-semantic", action="store_true",
                        help="also fail on text= and class-only selectors")
    parser.add_argument("--live-base-url", default="",
                        help="also resolve the signed-out contracts against a running site")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from demo_scenario import load_scenario

    paths = args.scenario or sorted((args.repo_root / "scripts/demo_videos/scenarios").glob("*.yaml"))
    index = SourceIndex.build(args.repo_root)
    report = {
        "contract_fingerprint": contract_fingerprint(),
        "contracts": [asdict(status) for status in check_contracts(args.repo_root)],
        "scenarios": [
            check_scenario(args.repo_root, load_scenario(path), index) for path in paths
        ],
    }
    broken = [entry for entry in report["contracts"] if not entry["ok"]]
    missing = []
    fragile = []
    unverifiable = []
    for scenario_report in report["scenarios"]:
        for selector in missing_scenario_selectors(scenario_report):
            missing.append(f"{scenario_report['app']}: {selector}")
        for selector in fragile_scenario_selectors(scenario_report):
            fragile.append(f"{scenario_report['app']}: {selector}")
        for selector in unverifiable_scenario_selectors(scenario_report):
            unverifiable.append(f"{scenario_report['app']}: {selector}")
    report["stale"] = bool(broken or missing)
    report["broken_contracts"] = broken
    report["missing_scenario_selectors"] = missing
    report["fragile_scenario_selectors"] = fragile
    report["unverifiable_scenario_selectors"] = unverifiable
    report["live"] = []
    if args.live_base_url:
        report["live"] = run_live_checks(args.live_base_url)
        broken_live = [entry for entry in report["live"] if not entry["ok"]]
        report["stale"] = report["stale"] or bool(broken_live)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "stale", "broken_contracts", "missing_scenario_selectors", "fragile_scenario_selectors",
        "unverifiable_scenario_selectors", "live")}, indent=2, sort_keys=True))
    # A missing selector means the video would show the wrong screen; a fragile
    # one means it follows a label that can be re-translated at any time. Only
    # the first is fatal, but both are printed so the report is not silent.
    if fragile:
        print(f"warning: {len(fragile)} selector(s) are not ids or data attributes:",
              file=sys.stderr)
        for selector in fragile:
            print(f"  {selector}", file=sys.stderr)
    if unverifiable:
        print(f"note: {len(unverifiable)} selector(s) cannot be checked statically "
              "(owner is outside this checkout); they are verified against the live DOM:",
              file=sys.stderr)
        for selector in unverifiable:
            print(f"  {selector}", file=sys.stderr)
    if report["stale"]:
        print("STALE: a control the videos depend on moved or vanished.", file=sys.stderr)
        return 1
    if fragile and args.strict_semantic:
        print("STRICT: replace these selectors with ids or data attributes.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
