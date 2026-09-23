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
from typing import Any, Dict, Iterator, List, Optional, Union

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
        except Exception:
            # Provider exceptions can contain credentials or response bodies.
            logger.error("[appmaker_agent] chat stream failed")
            yield {"type": "error", "error": "AI provider request failed"}


def resolve_chat_backend(user) -> Optional[Union[HubUserChatBackend, "FundedChatBackend"]]:
    """Return a BYOK backend, else the SciTeX-funded fallback.

    Server-funded calls go through the durable funded-chat executor (quota +
    spend ledger), adapted to the streaming interface by yielding the answer
    in chunks. No BYOK and no funded config → None (agent stays unavailable).
    """
    from apps.infra.llm_app.services import UserLLMService
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
    try:
        from apps.infra.llm_app.funded_chat.config import load_funded_chat_config

        config = load_funded_chat_config()
    except Exception:
        return None
    if not config.enabled:
        return None
    return FundedChatBackend(user)


class FundedChatBackend:
    """Streaming-shaped adapter over the durable funded-chat executor.

    Same ``stream()`` interface as :class:`HubUserChatBackend` so the
    app-agent chat works out of the box on the free allowance. The answer
    arrives as one durable result and is yielded in chunks.
    """

    _CHUNK = 120

    def __init__(self, user):
        self._user = user

    def stream(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        import json as _json
        import uuid as _uuid

        from apps.infra.llm_app.funded_chat.config import load_funded_chat_config
        from apps.infra.llm_app.funded_chat.provider import litellm_provider_call
        from apps.infra.llm_app.funded_chat.service import FundedChatService
        from apps.infra.llm_app.funded_chat.service import (
            FundedChatDenied as _Denied,
        )

        safe = [
            {"role": m.get("role", "user"), "content": str(m.get("content", ""))}
            for m in messages
            if isinstance(m, dict)
        ]
        if system:
            safe = [{"role": "system", "content": system}] + safe
        body = _json.dumps(
            {"messages": safe}, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        try:
            result = FundedChatService(config=load_funded_chat_config()).execute(
                self._user,
                idempotency_key=_uuid.uuid4().hex,
                request_body=body,
                provider_call=litellm_provider_call,
            )
            text = result.text or ""
        except _Denied as exc:
            logger.info("[appmaker_agent] funded chat denied: %s", exc.category)
            if exc.category == "quota_reached":
                yield {
                    "type": "error",
                    "error": "You have used today's free messages. Your draft is kept.",
                }
            else:
                yield {"type": "error", "error": "AI provider request failed"}
            return
        except Exception:
            logger.error("[appmaker_agent] funded chat failed")
            yield {"type": "error", "error": "AI provider request failed"}
            return
        for i in range(0, len(text), self._CHUNK):
            yield {"type": "chunk", "text": text[i : i + self._CHUNK]}
        yield {"type": "done"}


# EOF
