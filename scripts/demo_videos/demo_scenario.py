"""Declarative demo scenario: the YAML schema the recorder replays."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ACTIONS = {"goto", "click", "fill", "type", "press", "hover", "scroll", "wait"}
ACTIONS_NEEDING_SELECTOR = {"click", "fill", "type", "hover"}
ACTIONS_NEEDING_VALUE = {"goto", "fill", "type", "press"}
VIEWPORTS = ("desktop", "mobile")
STEP_KEYS = {"action", "narration", "selector", "value", "hold", "only"}


class ScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class Step:
    action: str
    narration: dict[str, str] = field(default_factory=dict)
    selector: dict[str, str] = field(default_factory=dict)
    value: dict[str, str] = field(default_factory=dict)
    hold: float = 0.8
    only: str = ""


@dataclass(frozen=True)
class Scenario:
    app: str
    title: dict[str, str]
    locales: dict[str, str]
    viewports: list[str]
    steps: list[Step] = field(default_factory=list)
    sign_in: bool = True

    @property
    def languages(self) -> list[str]:
        return list(self.locales)

    def steps_for(self, viewport: str) -> list[Step]:
        return [step for step in self.steps if step.only in ("", viewport)]


def parse_localized(raw, languages: list[str], where: str) -> dict[str, str]:
    """Text shared by every language, or a mapping with one entry per language."""
    if raw in (None, ""):
        return {}
    if not isinstance(raw, dict):
        return {language: str(raw) for language in languages}
    missing = [language for language in languages if not raw.get(language)]
    if missing:
        raise ScenarioError(f"{where}: missing languages {missing}")
    return {language: str(raw[language]) for language in languages}


def parse_locales(raw) -> dict[str, str]:
    if raw is None:
        return {"en": "en"}
    if isinstance(raw, list):
        return {str(language): str(language) for language in raw}
    if isinstance(raw, dict):
        return {
            str(language): str((settings or {}).get("locale", language))
            for language, settings in raw.items()
        }
    raise ScenarioError("languages: expected a list or a mapping of language to settings")


def parse_viewports(raw) -> list[str]:
    viewports = [str(name) for name in (raw or VIEWPORTS)]
    unknown = [name for name in viewports if name not in VIEWPORTS]
    if unknown:
        raise ScenarioError(f"viewports: unknown {unknown}, expected some of {list(VIEWPORTS)}")
    return viewports


def parse_step(raw: dict, position: int, languages: list[str]) -> Step:
    where = f"step {position}"
    unknown = set(raw) - STEP_KEYS
    if unknown:
        raise ScenarioError(f"{where}: unknown keys {sorted(unknown)}")
    step = Step(
        action=str(raw.get("action", "")),
        narration=parse_localized(raw.get("narration"), languages, f"{where} narration"),
        selector=parse_localized(raw.get("selector"), languages, f"{where} selector"),
        value=parse_localized(raw.get("value"), languages, f"{where} value"),
        hold=float(raw.get("hold", 0.8)),
        only=str(raw.get("only", "")),
    )
    if step.action not in ACTIONS:
        raise ScenarioError(f"{where}: action must be one of {sorted(ACTIONS)}")
    if step.action in ACTIONS_NEEDING_SELECTOR and not step.selector:
        raise ScenarioError(f"{where}: '{step.action}' needs a selector")
    if step.action in ACTIONS_NEEDING_VALUE and not step.value:
        raise ScenarioError(f"{where}: '{step.action}' needs a value")
    if step.only and step.only not in VIEWPORTS:
        raise ScenarioError(f"{where}: only must be one of {list(VIEWPORTS)}")
    if step.hold < 0:
        raise ScenarioError(f"{where}: hold must not be negative")
    return step


def parse_scenario(raw: dict) -> Scenario:
    for key in ("app", "title", "steps"):
        if not raw.get(key):
            raise ScenarioError(f"scenario is missing '{key}'")
    locales = parse_locales(raw.get("languages"))
    languages = list(locales)
    return Scenario(
        app=str(raw["app"]),
        title=parse_localized(raw["title"], languages, "title"),
        locales=locales,
        viewports=parse_viewports(raw.get("viewports")),
        steps=[parse_step(item, position, languages) for position, item in enumerate(raw["steps"], 1)],
        sign_in=bool(raw.get("sign_in", True)),
    )


def load_scenario(path: Path) -> Scenario:
    with open(path, encoding="utf-8") as handle:
        return parse_scenario(yaml.safe_load(handle))
