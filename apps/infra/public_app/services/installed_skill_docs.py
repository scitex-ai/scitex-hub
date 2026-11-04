"""Owner-filtered browser projection of Dev's public installed skill readers."""

from hashlib import sha256
from urllib.parse import urlencode

from .interface_catalog import _distribution_name


def installed_skill_guides(package):
    """List public identifiers and descriptions, never resource filesystem paths."""
    owner = _distribution_name(package)
    try:
        from scitex_dev.ecosystem import list_skills
        from scitex_dev.skill_registry import INSTALL_CAPABILITIES, SkillRegistryError
    except ImportError:
        return {"state": "unavailable", "entries": []}
    if "owned-skill-read-v1" not in INSTALL_CAPABILITIES:
        return {"state": "unavailable", "entries": []}
    try:
        listed = list_skills(package=owner)
        entries = []
        identities = set()
        for namespace, rows in listed.items():
            for row in rows:
                if _distribution_name(row.get("owner", "")) != owner:
                    return {"state": "invalid", "entries": []}
                name = row["name"]
                identity = (namespace, name)
                if identity in identities:
                    return {"state": "invalid", "entries": []}
                identities.add(identity)
                entries.append(
                    {
                        "owner": owner,
                        "namespace": namespace,
                        "name": name,
                        "description": row.get("description", ""),
                        "version": row.get("version", "unknown"),
                        "url": "/docs/web-api/skill/?"
                        + urlencode(
                            {
                                "package": owner,
                                "namespace": namespace,
                                "name": name,
                            }
                        ),
                    }
                )
        return {"state": "available", "entries": entries}
    except (SkillRegistryError, OSError, ValueError, KeyError, TypeError):
        return {"state": "invalid", "entries": []}


def read_installed_skill(package, namespace, name):
    """Admit an exact listed owner/namespace/name before the contained Dev read."""
    owner = _distribution_name(package)
    listing = installed_skill_guides(owner)
    if listing["state"] != "available":
        raise LookupError("Installed skill discovery is unavailable or invalid")
    matches = [
        row
        for row in listing["entries"]
        if row["namespace"] == namespace and row["name"] == name
    ]
    if len(matches) != 1:
        raise LookupError("No unique installed skill for this owner")
    from scitex_dev.ecosystem import get_skill
    from scitex_dev.skill_registry import SkillRegistryError

    try:
        content = get_skill(namespace, name, owner=owner)
    except (SkillRegistryError, OSError, ValueError) as exc:
        raise LookupError("Installed skill resource unavailable") from exc
    if content is None:
        raise LookupError("Installed skill resource unavailable")
    return {
        **matches[0],
        "content": content,
        "sha256": sha256(content.encode()).hexdigest(),
    }
