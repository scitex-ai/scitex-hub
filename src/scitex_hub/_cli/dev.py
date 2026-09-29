"""Operator/developer facade for SciTeX Hub setup and maintenance."""

from __future__ import annotations

from typing import Any

import click

from ._click_compat import spec_command_kwargs, spec_group_kwargs
from ._dev_dependencies import (
    collect_dev_doctor,
    collect_leaf_capability,
)
from ._dev_identity import collect_identity_report
from ._flags import emit_json, json_flag


def _json_requested(local_flag: bool) -> bool:
    """Honor either the leaf ``--json`` or the root CLI ``--json`` flag."""
    context = click.get_current_context(silent=True)
    while context is not None and context.parent is not None:
        context = context.parent
    root_value = bool(context and context.obj and context.obj.get("json"))
    return bool(local_flag or root_value)


def _emit_report(
    report: dict[str, Any], *, json_output: bool, fail_when_not_ready: bool
) -> None:
    if _json_requested(json_output):
        emit_json(report)
    else:
        click.echo(f"ready: {str(report['ready']).lower()}")
        for item in report.get("checks", []):
            mark = "PASS" if item["ok"] else "FAIL"
            click.echo(f"[{mark}] {item['name']}: {item.get('observed')!r}")
    if fail_when_not_ready and not report["ready"]:
        raise SystemExit(1)


@click.group(
    **spec_group_kwargs(
        summary="Audit and set up SciTeX Hub infrastructure.",
        examples=(("{prog} dev storage audit", "Measure the storage contract"),),
    )
)
def dev() -> None:
    """Find operator/developer setup, validation, and maintenance entry points.

    This group is never part of the customer SSH allowlist. It delegates generic
    mechanics to the SciTeX owner packages and never provides a generic root
    shell, raw argv, or privileged-path execution API.
    """


@dev.command(
    "doctor",
    **spec_command_kwargs(
        summary="Check delegated packages and operator prerequisites.",
        examples=(("{prog} dev doctor --json", "Emit dependency evidence"),),
    ),
)
@json_flag()
def dev_doctor(json_output: bool) -> None:
    """Check the public capabilities used by the dev facade."""
    _emit_report(
        collect_dev_doctor(),
        json_output=json_output,
        fail_when_not_ready=True,
    )


@dev.group(
    **spec_group_kwargs(
        summary="Plan initial SciTeX Hub infrastructure setup.",
        examples=(("{prog} dev setup plan --json", "Render the setup plan"),),
    )
)
def setup() -> None:
    """Plan setup; mutating leaves arrive only with typed Broker support."""


@setup.command(
    "plan",
    **spec_command_kwargs(
        summary="Render the ordered, non-mutating setup plan.",
        examples=(("{prog} dev setup plan --json", "Emit the plan as JSON"),),
    ),
)
@json_flag()
def setup_plan(json_output: bool) -> None:
    """Show the setup order without changing a host."""
    payload = {
        "schema_version": 1,
        "operation": "dev.setup.plan",
        "mutating": False,
        "ready": True,
        "checks": [],
        "stages": [
            "doctor",
            "storage",
            "identity",
            "resource",
            "ssh",
            "slurm",
            "container",
            "canary",
        ],
    }
    if _json_requested(json_output):
        emit_json(payload)
        return
    click.echo("SciTeX Hub setup plan (read-only):")
    for index, stage in enumerate(payload["stages"], 1):
        click.echo(f"  {index}. {stage}")


@dev.group(
    **spec_group_kwargs(
        summary="Discover Hub maintenance entry points.",
        examples=(
            ("{prog} dev maintenance list --json", "List owner-package entry points"),
        ),
    )
)
def maintenance() -> None:
    """Discover backup, restore, repair, rotation, and cleanup owners."""


@maintenance.command(
    "list",
    **spec_command_kwargs(
        summary="List maintenance responsibilities by owner package.",
        examples=(
            ("{prog} dev maintenance list --json", "Emit owner mappings as JSON"),
        ),
    ),
)
@json_flag()
def maintenance_list(json_output: bool) -> None:
    """List maintenance owner packages without invoking them."""
    payload = {
        "schema_version": 1,
        "operation": "dev.maintenance.list",
        "mutating": False,
        "ready": True,
        "checks": [],
        "owners": {
            "backup_restore": "scitex-storage",
            "archive_rotation": "scitex-storage",
            "remote_transport": "scitex-ssh",
            "slurm_jobs": "scitex-hpc",
            "runtime_images": "scitex-container",
            "host_resources": "scitex-resource",
        },
    }
    if _json_requested(json_output):
        emit_json(payload)
    else:
        for responsibility, owner in payload["owners"].items():
            click.echo(f"{responsibility}: {owner}")


def _leaf_validate(distribution: str, json_output: bool) -> None:
    _emit_report(
        collect_leaf_capability(distribution),
        json_output=json_output,
        fail_when_not_ready=True,
    )


@dev.group(
    **spec_group_kwargs(
        summary="Audit storage delegation and canary readiness.",
        examples=(("{prog} dev storage audit --json", "Audit storage capability"),),
    )
)
def storage() -> None:
    """Storage mechanics are delegated to scitex-storage."""


@storage.command(
    "audit",
    **spec_command_kwargs(
        summary="Report the delegated storage capability.",
        examples=(("{prog} dev storage audit --json", "Emit storage evidence"),),
    ),
)
@json_flag()
def storage_audit(json_output: bool) -> None:
    """Report storage rollout state without failing only because it is incomplete."""
    payload = collect_leaf_capability("scitex-storage")
    payload["operation"] = "dev.storage.audit"
    _emit_report(payload, json_output=json_output, fail_when_not_ready=False)


@storage.command(
    "validate",
    **spec_command_kwargs(
        summary="Validate the delegated storage contract.",
        examples=(
            ("{prog} dev storage validate --json", "Validate storage capability"),
        ),
    ),
)
@json_flag()
def storage_validate(json_output: bool) -> None:
    """Fail unless scitex-storage exposes the required public capability."""
    _leaf_validate("scitex-storage", json_output)


@storage.group(
    "canary",
    **spec_group_kwargs(
        summary="Manage the single-node storage canary.",
        examples=(
            ("{prog} dev storage canary plan --json", "Render the canary plan"),
        ),
    )
)
def storage_canary() -> None:
    """Plan canary work; apply/rollback arrive with the typed Broker."""


@storage_canary.command(
    "plan",
    **spec_command_kwargs(
        summary="Render the non-mutating compute-01 canary plan.",
        examples=(
            ("{prog} dev storage canary plan --json", "Emit the canary plan"),
        ),
    ),
)
@json_flag()
def storage_canary_plan(json_output: bool) -> None:
    """Render the bounded canary plan without a shell command or raw argv."""
    payload = {
        "schema_version": 1,
        "operation": "dev.storage.canary.plan",
        "mutating": False,
        "ready": False,
        "checks": [
            {
                "name": "typed_storage_runtime_validation",
                "ok": False,
                "observed": None,
                "expected": "scitex-storage runtime validator returns ready",
            },
            {
                "name": "rollback_path",
                "ok": False,
                "observed": None,
                "expected": "typed canary rollback is implemented and dry-reviewed",
            },
        ],
        "blockers": [
            "typed_storage_runtime_validation",
            "rollback_path",
        ],
        "target": {
            "node": "scitex-compute-01",
            "mountpoint": "/scitex-hub",
            "durable_directories": ["home", "projects", "datasets"],
            "scratch": "/scratch",
        },
        "required_controls": [
            "dedicated_nfs_export",
            "root_squash",
            "client_allowlist",
            "nas_side_provisioner",
            "fail_closed_mount_validation",
        ],
    }
    if _json_requested(json_output):
        emit_json(payload)
        return
    click.echo("Storage canary plan (read-only):")
    click.echo("  node: scitex-compute-01")
    click.echo("  mountpoint: /scitex-hub")
    click.echo("  scratch: /scratch (node-local)")


@dev.group(
    **spec_group_kwargs(
        summary="Audit the stable POSIX identity contract.",
        examples=(
            ("{prog} dev identity validate --json", "Validate identity ranges"),
        ),
    )
)
def identity() -> None:
    """Hub owns the ComputeIdentity policy; host sources are read-only."""


@identity.command(
    "validate",
    **spec_command_kwargs(
        summary="Validate stable UID/GID ranges.",
        examples=(
            ("{prog} dev identity validate --json", "Emit identity evidence"),
        ),
    ),
)
@json_flag()
def identity_validate(json_output: bool) -> None:
    """Validate host identity sources without changing accounts."""
    _emit_report(
        collect_identity_report(),
        json_output=json_output,
        fail_when_not_ready=True,
    )


def _register_leaf_group(
    *,
    name: str,
    distribution: str,
    summary: str,
) -> None:
    @dev.group(
        name,
        **spec_group_kwargs(
            summary=summary,
            examples=(
                (f"{{prog}} dev {name} validate --json", f"Validate {distribution}"),
            ),
        ),
    )
    def group() -> None:
        pass

    @group.command(
        "validate",
        **spec_command_kwargs(
            summary=f"Validate the {distribution} delegation.",
            examples=(
                (f"{{prog}} dev {name} validate --json", "Emit dependency evidence"),
            ),
        ),
    )
    @json_flag()
    def validate(json_output: bool) -> None:
        _leaf_validate(distribution, json_output)


_register_leaf_group(
    name="resource",
    distribution="scitex-resource",
    summary="Validate host-resource metrics delegation.",
)
_register_leaf_group(
    name="ssh",
    distribution="scitex-ssh",
    summary="Validate remote transport delegation.",
)
_register_leaf_group(
    name="slurm",
    distribution="scitex-hpc",
    summary="Validate SLURM/HPC delegation.",
)
_register_leaf_group(
    name="container",
    distribution="scitex-container",
    summary="Validate Apptainer/runtime delegation.",
)
