"""A2A AgentCard projection from scitex-agent-container/v3 YAML.

**Mirror of scitex_agent_container.a2a._card** (canonical projection).
This file enriches the canonical projection with orochi-fleet-specific
x-orochi extensions (identity_url, runtime_url, role_class, scheduling)
and request-aware base_url derived from Django request.

Until a shared dependency boundary is established, the canonical and
mirror must be kept in sync manually. Diverging field semantics is a
bug; diverging extension namespaces is by design (sac uses
x-scitex-agent-container, orochi adds x-orochi on top).

Reads agent definitions from ``$SCITEX_OROCHI_AGENTS_DIR`` (default
``~/.scitex/orochi/shared/agents/`` -- synced via dotfiles to NAS) and
projects them into A2A-compliant AgentCard JSON.

URL construction is request-aware: pass ``base_url`` from
``request.build_absolute_uri('/')`` so each AgentCard advertises the
URL the client actually used. This keeps cards correct whether served
from ``a2a.scitex.ai`` (canonical) or any future mirror.

Non-standard Orochi concepts (cardinality, host/hosts scheduling,
runtime/model) live under the namespaced ``x-orochi`` extension block.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from apps.infra.platform_app.services.paths import resolve_within

DEFAULT_AGENTS_DIR = Path.home() / ".scitex" / "orochi" / "shared" / "agents"
DEFAULT_BASE_URL = "https://a2a.scitex.ai"

# An agent name is one directory segment: letters, digits, dot, underscore,
# dash. It is NOT a path, so "." / ".." / anything with a separator is not a
# name that could have been meant. Matches the charset the fleet already uses
# for agent ids (scitex-hub, scitex-agent-container, clew-a-001-...).
_AGENT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _agents_dir() -> Path:
    p = os.environ.get("SCITEX_OROCHI_AGENTS_DIR")
    return Path(p) if p else DEFAULT_AGENTS_DIR


def _scheduling(spec: dict) -> dict:
    if "hosts" in spec:
        return {"mode": "multi-instance", "hosts": spec["hosts"]}
    if "host" in spec:
        h = spec["host"]
        priority = h if isinstance(h, list) else ([h] if h else [])
        return {"mode": "singleton", "priority": priority}
    return {"mode": "singleton", "priority": []}


def _read_description(agent_dir: Path, name: str) -> str:
    readme = agent_dir / "README.md"
    if not readme.exists():
        return f"Orochi agent: {name}"
    for line in readme.read_text().splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("# ").strip()
    return f"Orochi agent: {name}"


def project(name: str, v3: dict, agent_dir: Path, base_url: str) -> dict[str, Any]:
    base = base_url.rstrip("/")
    meta_labels = (v3.get("metadata", {}) or {}).get("labels", {}) or {}
    spec = v3.get("spec", {}) or {}
    caps_csv = meta_labels.get("capabilities", "") or ""
    capabilities_tags = [c.strip() for c in caps_csv.split(",") if c.strip()]
    required_skills = (spec.get("skills", {}) or {}).get("required", []) or []
    role = meta_labels.get("role", "unknown")
    function = meta_labels.get("function", "")

    return {
        "name": name,
        "description": _read_description(agent_dir, name),
        "version": v3.get("apiVersion", "scitex-agent-container/v3"),
        "url": f"{base}/v1/agents/{name}",
        "provider": {
            "organization": meta_labels.get("team", "orochi"),
            "url": "https://scitex.ai",
        },
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "authentication": {"schemes": ["bearer"]},
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": f"{name}.{role}",
                "name": role,
                "description": (
                    function.replace(",", ", ")
                    if function
                    else f"{role} for {meta_labels.get('team', 'orochi')}"
                ),
                "tags": sorted(set(capabilities_tags + required_skills)),
            }
        ],
        "x-orochi": {
            "role_class": role,
            "cardinality": meta_labels.get("cardinality"),
            "scheduling": _scheduling(spec),
            "runtime": spec.get("runtime"),
            "model": spec.get("model"),
            "multiplexer": spec.get("multiplexer"),
            "required_skills": required_skills,
            "identity_url": f"https://git.scitex.ai/{name}",
            "runtime_url": "https://scitex-orochi.com",
        },
    }


def list_agents() -> list[str]:
    d = _agents_dir()
    if not d.is_dir():
        return []
    out: list[str] = []
    for child in sorted(d.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        if (child / f"{child.name}.yaml").exists():
            out.append(child.name)
    return out


def load_card(name: str, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any] | None:
    # `name` arrives from the PUBLIC route /v1/agents/<name>, so it is
    # untrusted. An agent name is a single directory segment by definition;
    # anything that is not one cannot name an agent, so reject it before it
    # reaches the filesystem rather than trying to sanitise it.
    if not _AGENT_NAME_RE.match(name or ""):
        return None

    d = _agents_dir()
    agent_dir = resolve_within(d, name)
    if agent_dir is None:
        return None

    yaml_path = resolve_within(agent_dir, f"{name}.yaml")
    if yaml_path is None or not yaml_path.exists():
        return None

    v3 = yaml.safe_load(yaml_path.read_text()) or {}
    return project(name, v3, agent_dir, base_url)


def fleet_index(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    base = base_url.rstrip("/")
    return {
        "agents": [{"name": n, "url": f"{base}/v1/agents/{n}"} for n in list_agents()]
    }


def fleet_card(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    base = base_url.rstrip("/")
    return {
        "name": "orochi",
        "description": "Orochi Multi-Agent Fleet — self-hosted Claude Code agents.",
        "version": "scitex-orochi/1",
        "url": base,
        "provider": {"organization": "orochi", "url": "https://scitex.ai"},
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "authentication": {"schemes": ["bearer"]},
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": "orochi.fleet",
                "name": "fleet",
                "description": "Multi-agent fleet — see /v1/agents/ for members.",
                "tags": ["multi-agent", "claude-code", "scitex-orochi"],
            }
        ],
        "x-orochi": {
            "agents_index_url": f"{base}/v1/agents/",
            "members": list_agents(),
            "identity_provider": "https://git.scitex.ai",
            "runtime_hub": "https://scitex-orochi.com",
        },
    }


__all__ = [
    "list_agents",
    "load_card",
    "fleet_index",
    "fleet_card",
    "project",
    "DEFAULT_BASE_URL",
]
