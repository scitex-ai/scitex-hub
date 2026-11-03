#!/usr/bin/env python3
"""Add four explicit human-owned MNIST demo cards through the public Cards API.

Dry-run is the default. --apply adds missing fixture rows, never updates rows.
--cleanup tombstones only unchanged fixture rows with no external references.
SCITEX_STORE_DSN must explicitly name the authorized store. Use the normal
human CLI credential/pgpass; never borrow a web reader or native agent identity.
"""
from __future__ import annotations

import argparse
import pwd
import hashlib
import json
import os
from pathlib import Path

MARKER = "scitex-mnist-board-showcase-20261103"
NOTE = (
    "Synthetic workflow example for the SciTeX MNIST showcase; these statuses "
    "are illustrative UI stages, not verified research progress. No agent, "
    "model, session, command, or compute job is requested. Fixture: " + MARKER
)
ROWS = (
    ("overview", "Demo: MNIST workflow overview", "goal", None),
    ("references", "Demo: Review MNIST data and reference sources", "done", None),
    ("comparison", "Demo: Compare MNIST model metrics", "blocked", "operator-decision"),
    ("report", "Demo: Assemble the MNIST report", "blocked", "operator-decision"),
)


def fixture_rows(owner: str) -> list[dict]:
    return [dict(
        id=f"demo-mnist-showcase-20261103-{key}", title=title, status=status,
        kind="status", project=f"{owner}/example-project-mnist", scope=MARKER,
        created_by=owner, assignee=owner, agent=owner, note=NOTE,
        blocker=blocker, collaborators=[], subscribers=[],
        notify={"events": {"created": []}, "mute": [owner]},
    ) for key, title, status, blocker in ROWS]


def signature(row: dict, expected: dict) -> bool:
    return all(row.get(k) == v for k, v in expected.items())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--cleanup", action="store_true")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--seed-receipt", type=Path, help="original apply receipt required for cleanup")
    args = parser.parse_args()
    store = os.environ.get("SCITEX_STORE_DSN", "")
    if not store:
        raise ValueError("an explicit authorized SCITEX_STORE_DSN is required")
    owner = pwd.getpwuid(os.getuid()).pw_name
    # Direct read-only SQL is only a health/target attestation; all mutations
    # below go through public Cards functions with their normal validators.
    import psycopg
    with psycopg.connect(store, connect_timeout=10) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        database, role, readonly = connection.execute(
            "SELECT current_database(), current_user, current_setting(%s)",
            ("transaction_read_only",),
        ).fetchone()
        if readonly != "on":
            raise RuntimeError("backend read-only health attestation failed")
    import scitex_cards as cards
    from scitex_cards._notify import resolve_recipients
    from scitex_cards._runnable import runnable_tasks
    from scitex_cards._validate import _validate_tasks

    plans = fixture_rows(owner)
    _validate_tasks(plans, source="MNIST showcase fixture", strict=True)
    if runnable_tasks(plans).tasks:
        raise RuntimeError("fixture would be runnable; refusing")
    for row in plans:
        if resolve_recipients({"type": "created"}, row, store=store):
            raise RuntimeError("fixture would notify a recipient; refusing")
    existing = {}
    for row in plans:
        try:
            actual = cards.get_task(store=store, task_id=row["id"])
        except cards.TaskNotFoundError:
            continue
        if not signature(actual, row):
            raise RuntimeError("an existing fixture ID differs; refusing overwrite")
        existing[row["id"]] = actual
    result = {
        "backend_health": {"database": database, "role": role, "read_only": readonly},
        "fixture": MARKER, "project": plans[0]["project"],
        "human_owner": owner, "mode": "cleanup" if args.cleanup else "apply" if args.apply else "dry-run",
        "fixture_ids": [r["id"] for r in plans], "created": [], "existing": sorted(existing),
        "external_dispatch_handlers": 0, "created_notification_recipients": 0,
        "runnable_fixture_rows": 0, "removed": [],
        "cards_module": str(Path(cards.__file__).resolve()), "cards_version": cards.__version__,
        "note": "kind=status is descriptive; non-runnable states/blockers are checked separately. Builtin notifications are muted separately from external plugin dispatch.",
    }
    if args.cleanup:
        if not args.seed_receipt or args.seed_receipt.stat().st_size > 131072:
            raise ValueError("cleanup requires the original bounded seed receipt")
        original = json.loads(args.seed_receipt.read_text())
        if original.get("fixture") != MARKER or original.get("human_owner") != owner:
            raise ValueError("cleanup receipt identity differs")
        for key, row in existing.items():
            digest = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()
            if original.get("persisted_fixture_row_sha256", {}).get(key) != digest:
                raise RuntimeError("a fixture was changed since creation; cleanup refused")
        all_rows = cards.list_tasks(store=store, scope="")
        fixture_ids = set(result["fixture_ids"])
        for row in all_rows:
            refs = set(row.get("depends_on") or ()) | set(row.get("blocks") or ()) | {row.get("parent")}
            if row.get("id") not in fixture_ids and refs & fixture_ids:
                raise RuntimeError("other tasks refer to fixture rows; cleanup refused")
        for row in plans:
            if row["id"] in existing:
                cards.delete_task(store=store, task_id=row["id"])
                result["removed"].append(row["id"])
    elif args.apply:
        for row in plans:
            if row["id"] in existing:
                continue
            saved = cards.add_task(store, entry_points=(), expected_revision=0, **row)
            if not signature(saved, row):
                raise RuntimeError("saved fixture differs from plan")
            result["created"].append(row["id"])
        actual = [cards.get_task(store=store, task_id=row["id"]) for row in plans]
        if runnable_tasks(actual).tasks or any(resolve_recipients({"type": "created"}, row, store=store) for row in actual):
            raise RuntimeError("persisted fixture violated admission controls")
        result["persisted_fixture_row_sha256"] = {row["id"]: hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest() for row in actual}
        result["persisted_fixture_sha256"] = hashlib.sha256(json.dumps(actual, sort_keys=True, default=str).encode()).hexdigest()
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump(result, output, indent=2)
            output.write("\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Store errors can contain a connection string. Keep values private.
        print(json.dumps({"pass": False, "error_type": type(exc).__name__}))
        raise SystemExit(1)
