#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The app-maker agent: skills, system prompt and the user's LLM backend.

Skills are plain named text blocks so another harness (e.g. Hermes) can load
the same list instead of this module's flat system prompt. The chat itself
streams through ``scitex_app._chat`` over the hub's bring-your-own-key
provider registration (llm_app), never a hardcoded vendor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

SDK_SKILL_FILES = (
    "SKILL.md",
    "12_app-develop.md",
    "15_manifest-schema.md",
    "17_app-develop-frontend.md",
    "19_files-sdk.md",
)

EDIT_PROTOCOL = """You are the SciTeX app-maker agent. You help a researcher build a
Work app for their own experiment inside this project.

To change a file, reply with ONE fenced code block per file whose info string
is the language followed by `path=<path relative to the project root>` and
whose body is the COMPLETE new file content, for example:

```html path=my_app/templates/my_app/index_partial.html
...whole file...
```

The user applies each block with one click, so never send partial files or
diffs inside such a block. Keep edits small and explain them in one or two
sentences. Only touch files inside this project. Never put secrets in code.
"""


@dataclass(frozen=True)
class Skill:
    name: str
    text: str


def _read_sdk_skill(filename: str) -> str:
    try:
        root = resources.files("scitex_app") / "_skills" / "scitex-app"
        return (root / filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        logger.warning("[appmaker_agent] SDK skill %s not found", filename)
        return ""


def build_skills(project_dir: Optional[Path]) -> List[Skill]:
    skills = [Skill("appmaker-edit-protocol", EDIT_PROTOCOL)]
    agents_md = project_dir / "AGENTS.md" if project_dir else None
    if agents_md is not None and agents_md.is_file():
        skills.append(Skill("app-agents-md", agents_md.read_text(encoding="utf-8")))
    for filename in SDK_SKILL_FILES:
        text = _read_sdk_skill(filename)
        if text:
            skills.append(Skill(f"scitex-app/{filename}", text))
    return skills


def build_system_prompt(skills: List[Skill], files: List[str]) -> str:
    parts = [f'<skill name="{s.name}">\n{s.text}\n</skill>' for s in skills]
    if files:
        parts.append("Files in this project:\n" + "\n".join(files))
    return "\n\n".join(parts)


class HubUserChatBackend:
    """``scitex_app._chat.ChatBackend`` over the user's registered AI provider."""

    def __init__(self, model: str, api_key: Optional[str]):
        self._model = model
        self._api_key = api_key

    def stream(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        import litellm

        msgs = ([{"role": "system", "content": system}] if system else []) + list(
            messages
        )
        try:
            response = litellm.completion(
                model=model or self._model,
                messages=msgs,
                api_key=self._api_key,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield {"type": "chunk", "text": delta.content}
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("[appmaker_agent] chat stream failed")
            yield {"type": "error", "error": str(exc)}


def resolve_chat_backend(user) -> Optional[HubUserChatBackend]:
    """The same provider Chat uses: the user's own key, else the campaign key.

    Returns None when nothing is configured — the caller shows the
    "connect an AI provider" state.
    """
    from apps.infra.llm_app.services import UserLLMService
    from apps.infra.llm_app.services.campaign_service import (
        get_campaign_config,
        is_campaign_enabled,
    )
    from apps.infra.llm_app.utils import litellm_model_string

    service = UserLLMService(user)
    if (
        service.connection
        and service.llm_connection
        and service.llm_connection.default_model
    ):
        model = litellm_model_string(
            service.connection.service, service.llm_connection.default_model
        )
        return HubUserChatBackend(
            model or service.llm_connection.default_model,
            service.connection.get_api_key(),
        )
    if is_campaign_enabled():
        config = get_campaign_config()
        return HubUserChatBackend(f"anthropic/{config['model']}", config["api_key"])
    return None


# EOF
