"""Declarative demo scenario: the YAML schema the recorder replays."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ACTIONS = {"goto", "click", "fill", "type", "press", "hover", "scroll", "wait"}
ACTIONS_NEEDING_SELECTOR = {"click", "fill", "type", "hover"}
ACTIONS_NEEDING_VALUE = {"goto", "fill", "type", "press"}
VIEWPORTS = {"desktop", "mobile"}
STEP_KEYS = {"action", "narration", "selector", "value", "hold", "only"}


class ScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class Step:
    action: str
    narration: dict[str, str] = field(default_factory=dict)
    selector: str = ""
    value: str = ""
    hold: float = 0.8
    only: str = ""


@dataclass(frozen=True)
class Scenario:
    app: str
    title: dict[str, str]
    languages: list[str]
    steps: list[Step] = field(default_factory=list)
    sign_in: bool = True

    def steps_for(self, viewport: str) -> list[Step]:
        return [step for step in self.steps if step.only in ("", viewport)]


def parse_localized(raw, languages: list[str], where: str) -> dict[str, str]:
    if raw in (None, ""):
        return {}
    if isinstance(raw, str):
        raw = {languages[0]: raw}
    if not isinstance(raw, dict):
        raise ScenarioError(f"{where}: expected text or a language mapping")
    missing = [language for language in languages if not raw.get(language)]
    if missing:
        raise ScenarioError(f"{where}: missing languages {missing}")
    return {language: str(raw[language]) for language in languages}


def parse_step(raw: dict, position: int, languages: list[str]) -> Step:
    where = f"step {position}"
    unknown = set(raw) - STEP_KEYS
    if unknown:
        raise ScenarioError(f"{where}: unknown keys {sorted(unknown)}")
    step = Step(
        action=str(raw.get("action", "")),
        narration=parse_localized(raw.get("narration"), languages, where),
        selector=str(raw.get("selector", "")),
        value=str(raw.get("value", "")),
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
        raise ScenarioError(f"{where}: only must be one of {sorted(VIEWPORTS)}")
    if step.hold < 0:
        raise ScenarioError(f"{where}: hold must not be negative")
    return step


def parse_scenario(raw: dict) -> Scenario:
    for key in ("app", "title", "steps"):
        if not raw.get(key):
            raise ScenarioError(f"scenario is missing '{key}'")
    languages = [str(language) for language in raw.get("languages", ["en"])]
    steps = [
        parse_step(item, position, languages)
        for position, item in enumerate(raw["steps"], 1)
    ]
    return Scenario(
        app=str(raw["app"]),
        title=parse_localized(raw["title"], languages, "title"),
        languages=languages,
        steps=steps,
        sign_in=bool(raw.get("sign_in", True)),
    )


def load_scenario(path: Path) -> Scenario:
    with open(path, encoding="utf-8") as handle:
        return parse_scenario(yaml.safe_load(handle))
