"""Explicit plan/apply for an existing MNIST Writer workspace; never a GET hook."""

import json
import os
import re
import tempfile
from pathlib import Path

from ..writer_workspace_layout import WRITER_WORKSPACE_RELPATH
from ._mnist_commit import publish_section, restore_section_if_ours, stage_sections
from ._mnist_facts import (
    DemoSeedRefused,
    digest,
    jailed,
    load_facts,
    read_member,
    section_text,
    showcase_note,
)

SCHEMA = "scitex-hub.writer-mnist-demo/v1"
NOTE_RELPATH = "SHOWCASE-MNIST.md"
STATE_RELPATH = ".scitex/showcase/writer-mnist-v1.json"
BACKUP_RELPATH = ".scitex/showcase/writer-mnist-v1-originals"
TEMPLATE_ROOT = Path(__file__).with_name("payload") / "writer_template_v24319"
SECTIONS = ("abstract", "methods", "results")


def _json(data):
    return (json.dumps(data, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _root(project_root):
    path = Path(project_root).absolute()
    if path.is_symlink() or not path.is_dir():
        raise DemoSeedRefused("Authorize an existing regular project directory")
    return path.resolve(strict=True)


def _section_path(name):
    return f"{WRITER_WORKSPACE_RELPATH}/01_manuscript/contents/{name}.tex"


def _workspace(root):
    workspace = jailed(root, WRITER_WORKSPACE_RELPATH)
    for name in ("00_shared", "01_manuscript", "02_supplementary", "03_revision"):
        if not jailed(root, f"{WRITER_WORKSPACE_RELPATH}/{name}").is_dir():
            raise DemoSeedRefused(
                "An existing initialized Writer workspace is required"
            )
    return workspace


def _writer(root):
    from scitex_writer import Writer

    return Writer(_workspace(root), git_strategy=None)


def _prior(root):
    path = jailed(root, STATE_RELPATH, missing=True)
    if not path.exists():
        return None, None
    raw = read_member(root, STATE_RELPATH)
    try:
        value = json.loads(raw)
        if (
            value["schema"] != SCHEMA
            or set(value["seeded_sections"]) != set(SECTIONS)
            or not re.fullmatch(r"[0-9a-f]{64}", value["showcase_note_sha256"])
        ):
            raise DemoSeedRefused("Unsupported previous demo admission")
        for name in SECTIONS:
            expected = digest((TEMPLATE_ROOT / f"{name}.tex").read_bytes())
            if value["original_sections"][name] != expected:
                raise DemoSeedRefused(
                    "Previous admission does not identify reviewed template originals"
                )
            if digest(read_member(root, f"{BACKUP_RELPATH}/{name}.tex")) != expected:
                raise DemoSeedRefused(
                    "Previous original backup differs from the template identity"
                )
            if not isinstance(value["seeded_sections"][name], str) or not re.fullmatch(
                r"[0-9a-f]{64}", value["seeded_sections"][name]
            ):
                raise DemoSeedRefused("Invalid previous seed identity")
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, DemoSeedRefused):
            raise
        raise DemoSeedRefused("Malformed previous demo admission") from exc
    return value, digest(raw)


def plan_mnist_writer_demo(project_root):
    """Pure filesystem plan: no Writer construction, refresh, directory creation or compile.

    Only exact reviewed template bytes or the exact previous recorded seed may
    be replaced. Any authored section blocks the entire apply, preserving it.
    The returned plan is tied to the observed bundle, state and section bytes.
    """
    root = _root(project_root)
    _workspace(root)
    facts, inputs = load_facts(root)
    prior, previous_hash = _prior(root)
    rendered = section_text(facts)
    note = showcase_note(facts, inputs).encode()
    note_path = jailed(root, NOTE_RELPATH, missing=True)
    note_before = (
        digest(read_member(root, NOTE_RELPATH)) if note_path.exists() else None
    )
    note_action = "create" if note_before is None else "preserve-authored"
    if prior and note_before == prior.get("showcase_note_sha256"):
        note_action = "unchanged" if note_before == digest(note) else "seed"
    rows = []
    for name in SECTIONS:
        current = read_member(root, _section_path(name))
        template_hash = digest((TEMPLATE_ROOT / f"{name}.tex").read_bytes())
        current_hash, target_hash = digest(current), digest(rendered[name].encode())
        allowed = {template_hash}
        if prior:
            allowed.add(prior["seeded_sections"][name])
        action = "preserve-authored"
        if current_hash in allowed:
            action = "unchanged" if current_hash == target_hash else "seed"
        rows.append(
            {
                "section": name,
                "before_sha256": current_hash,
                "after_sha256": target_hash,
                "action": action,
            }
        )
    plan = {
        "schema": SCHEMA,
        "inputs": inputs,
        "previous_state_sha256": previous_hash,
        "sections": rows,
        "showcase_note": {
            "before_sha256": note_before,
            "after_sha256": digest(note),
            "action": note_action,
        },
        "applicable": note_action != "preserve-authored"
        and all(r["action"] != "preserve-authored" for r in rows),
    }
    plan["plan_sha256"] = digest(_json(plan))
    return plan


def _create_original(root, name, original):
    path = jailed(root, f"{BACKUP_RELPATH}/{name}.tex", missing=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    jailed(root, f"{BACKUP_RELPATH}/{name}.tex", missing=True)
    if path.exists():
        if read_member(root, f"{BACKUP_RELPATH}/{name}.tex") != original:
            raise DemoSeedRefused(
                "An existing original backup must never be overwritten"
            )
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())


def apply_mnist_writer_demo(project_root, *, expected_plan_sha256):
    """Explicitly apply a reviewed plan using public Writer section operations.

    The caller authorizes the project root and supplies the reviewed plan hash.
    This operation never compiles, touches bibliography or refreshes scripts.
    It records originals and stages real Writer writes before atomic publication.
    Individual replacements are atomic; the whole batch is not a transaction.
    Concurrent editors must not be used during this explicit admission.
    """
    root = _root(project_root)
    plan = plan_mnist_writer_demo(root)
    if plan["plan_sha256"] != expected_plan_sha256 or not plan["applicable"]:
        raise DemoSeedRefused("The reviewed plan changed or contains authored sections")
    prior, _ = _prior(root)
    facts, inputs = load_facts(root)
    if inputs != plan["inputs"]:
        raise DemoSeedRefused("Computed inputs changed after plan admission")
    rendered = section_text(facts)
    writer = _writer(root)
    originals = {}
    for row in plan["sections"]:
        name = row["section"]
        current = read_member(root, _section_path(name))
        # Public reading must agree with the byte-level admission, not silently
        # accept its missing-file/alternate-encoding fallbacks.
        if writer.read_section(name).encode("utf-8") != current:
            raise DemoSeedRefused(
                "Writer section differs from the admitted UTF-8 bytes"
            )
        originals[name] = current
    if (
        all(row["action"] == "unchanged" for row in plan["sections"])
        and prior
        and plan["showcase_note"]["action"] == "unchanged"
    ):
        return {
            "schema": SCHEMA,
            "changed": [],
            "state_sha256": digest(read_member(root, STATE_RELPATH)),
            "showcase_note_changed": False,
        }
    # The original template backups are immutable across later explicit reseeds.
    for name in SECTIONS:
        original = (
            (TEMPLATE_ROOT / f"{name}.tex").read_bytes() if prior else originals[name]
        )
        _create_original(root, name, original)
    changed = []
    note_before = (
        read_member(root, NOTE_RELPATH)
        if plan["showcase_note"]["before_sha256"]
        else None
    )
    note_after = showcase_note(facts, inputs).encode()
    note_written = False
    with stage_sections(
        root, plan["sections"], originals, rendered, _section_path
    ) as prepared:
        try:
            for row in plan["sections"]:
                name = row["section"]
                if row["action"] == "unchanged":
                    continue
                publish_section(
                    root, _section_path(name), row["before_sha256"], prepared[name]
                )
                changed.append(name)
                if (
                    digest(read_member(root, _section_path(name)))
                    != row["after_sha256"]
                ):
                    raise DemoSeedRefused(
                        "Written section identity could not be verified"
                    )
            note_path = jailed(root, NOTE_RELPATH, missing=True)
            current_note = (
                read_member(root, NOTE_RELPATH) if note_path.exists() else None
            )
            if current_note != note_before:
                raise DemoSeedRefused("Showcase note changed after plan admission")
            if plan["showcase_note"]["action"] != "unchanged":
                fd, temporary = tempfile.mkstemp(prefix=".mnist-note-", dir=root)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(note_after)
                        stream.flush()
                        os.fsync(stream.fileno())
                    jailed(root, NOTE_RELPATH, missing=True)
                    os.replace(temporary, note_path)
                    note_written = True
                finally:
                    Path(temporary).unlink(missing_ok=True)
            state = {
                "schema": SCHEMA,
                "inputs": plan["inputs"],
                "provenance_scope": "Existing OpenML/logistic-regression/kNN example; excludes template Torch/UMAP/SVM scripts",
                "independently_verified": False,
                "showcase_note_sha256": digest(note_after),
                "original_sections": {
                    n: digest((TEMPLATE_ROOT / f"{n}.tex").read_bytes())
                    for n in SECTIONS
                },
                "seeded_sections": {n: digest(rendered[n].encode()) for n in SECTIONS},
            }
            state_path = jailed(root, STATE_RELPATH, missing=True)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            jailed(root, STATE_RELPATH, missing=True)
            _, state_hash = _prior(root)
            if state_hash != plan["previous_state_sha256"]:
                raise DemoSeedRefused("Previous admission changed before state commit")
            fd, temporary = tempfile.mkstemp(
                prefix=".writer-mnist-", dir=state_path.parent
            )
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(_json(state))
                    stream.flush()
                    os.fsync(stream.fileno())
                jailed(root, STATE_RELPATH, missing=True)
                os.replace(temporary, state_path)
            finally:
                Path(temporary).unlink(missing_ok=True)
        except Exception:
            if note_written and read_member(root, NOTE_RELPATH) == note_after:
                if note_before is None:
                    jailed(root, NOTE_RELPATH).unlink()
                else:
                    jailed(root, NOTE_RELPATH).write_bytes(note_before)
            # Roll back only writes whose exact seeded bytes are still ours. Keep
            # original backups and any concurrently authored content untouched.
            for name in reversed(changed):
                restore_section_if_ours(
                    root,
                    _section_path(name),
                    digest(rendered[name].encode()),
                    prepared[name],
                )
            raise

    return {
        "schema": SCHEMA,
        "changed": changed,
        "state_sha256": digest(read_member(root, STATE_RELPATH)),
        "showcase_note_changed": note_written,
    }
