"""A final normal resolution must repair incompatible cached installations."""

import base64
import csv
import hashlib
import importlib.metadata as metadata
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import zipfile
from email.message import Message
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/deploy/installed_runtime_roots.py"
SPEC = importlib.util.spec_from_file_location("owned_runtime_roots", SCRIPT)
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)


@pytest.mark.parametrize(
    "name", ["", "bad\npackage", "project @ https://example.org", None]
)
def test_metadata_cannot_inject_requirement_lines_or_urls(name):
    with pytest.raises(ValueError):
        COLLECTOR.installed_names([SimpleNamespace(metadata={"Name": name})])


def wheel(directory, name, version, requires=(), extras=()):
    module = name.replace("-", "_")
    info = f"{module}-{version}.dist-info"
    members = {
        f"{module}/__init__.py": b"",
        f"{info}/METADATA": (
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
            + "".join(f"Requires-Dist: {requirement}\n" for requirement in requires)
            + "".join(f"Provides-Extra: {extra}\n" for extra in extras)
        ).encode(),
        f"{info}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    record = io.StringIO()
    rows = csv.writer(record)
    for path, content in members.items():
        digest = (
            base64.urlsafe_b64encode(hashlib.sha256(content).digest())
            .decode()
            .rstrip("=")
        )
        rows.writerow((path, f"sha256={digest}", len(content)))
    rows.writerow((f"{info}/RECORD", "", ""))
    members[f"{info}/RECORD"] = record.getvalue().encode()
    with zipfile.ZipFile(
        directory / f"{module}-{version}-py3-none-any.whl", "w"
    ) as archive:
        for path, content in members.items():
            archive.writestr(path, content)


def test_one_normal_resolution_repairs_a_real_incompatible_cached_graph(tmp_path):
    uv = shutil.which("uv")
    assert uv, "The deployment integration runner requires its normal uv tool"
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    wheel(wheelhouse, "runtime-graph-dependency", "1.0")
    wheel(wheelhouse, "runtime-graph-dependency", "2.0")
    wheel(wheelhouse, "runtime-graph-holder", "1.0", ["runtime-graph-dependency<2"])
    environment = tmp_path / "env"

    def run(*args, check=True):
        return subprocess.run(
            args, cwd=tmp_path, capture_output=True, text=True, check=check
        )

    run(uv, "venv", "--python", sys.executable, str(environment))
    python = str(environment / "bin/python")
    install = [
        uv,
        "pip",
        "install",
        "--python",
        python,
        "--no-index",
        "--find-links",
        str(wheelhouse),
    ]
    run(*install, "runtime-graph-holder==1.0")
    # Both are normal dependency-resolving installs, reproducing Docker's
    # separate cache-layer transactions without any --no-deps shortcut.
    run(*install, "runtime-graph-dependency==2.0")
    assert run(uv, "pip", "check", "--python", python, check=False).returncode != 0
    roots = tmp_path / "runtime-roots.in"
    lock = tmp_path / "runtime.lock"
    site = (
        environment
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    COLLECTOR.write_inputs(
        roots,
        lock,
        metadata.distributions(path=[site]),
        explicit_roots=("runtime-graph-holder",),
        local_project=None,
    )
    assert roots.read_text().splitlines() == ["runtime-graph-holder"]
    run(
        uv,
        "pip",
        "compile",
        "--no-index",
        "--find-links",
        str(wheelhouse),
        str(roots),
        "-o",
        str(lock),
    )
    run(
        uv,
        "pip",
        "sync",
        "--python",
        python,
        "--no-index",
        "--find-links",
        str(wheelhouse),
        str(lock),
    )
    assert run(uv, "pip", "check", "--python", python).returncode == 0
    result = run(
        python,
        "-c",
        "import importlib.metadata as m,json;print(json.dumps(m.version('runtime-graph-dependency')))",
    )
    assert json.loads(result.stdout) == "1.0"


def distribution(name, requires=(), extras=(), version="1.0"):
    message = Message()
    message["Name"] = name
    for extra in extras:
        message["Provides-Extra"] = extra
    return SimpleNamespace(metadata=message, requires=list(requires), version=version)


def test_first_party_and_installed_optional_scientific_capabilities_survive():
    installed = [
        distribution(
            "scitex-science",
            [
                "owned-heavy; extra == 'scientific'",
                "foreign-platform; sys_platform == 'unsupported-scitex-platform'",
                "missing-optional; extra == 'scientific'",
            ],
            extras=["scientific"],
        ),
        distribution("figrecipe", ["owned-graphics"]),
        distribution("owned-heavy"),
        distribution("owned-graphics"),
        distribution("foreign-platform"),
        distribution("unreferenced-helper"),
    ]
    roots, preferences = COLLECTOR.resolution_inputs(installed, explicit_roots=())
    assert (roots, "unreferenced-helper==1.0" in preferences) == (
        ["figrecipe", "owned-graphics", "owned-heavy", "scitex-science"],
        True,
    )


def test_invalid_cached_version_cannot_inject_preference_lines():
    with pytest.raises(ValueError):
        COLLECTOR.resolution_inputs(
            [distribution("scitex-owner", version="1.0\nother>=2")]
        )


def test_ambiguous_cached_versions_refuse_before_resolution():
    with pytest.raises(ValueError, match="Ambiguous"):
        COLLECTOR.resolution_inputs(
            [distribution("scitex-owner"), distribution("scitex_owner", version="2.0")]
        )


def test_malformed_owned_requirement_is_not_silently_omitted():
    with pytest.raises(ValueError):
        COLLECTOR.resolution_inputs(
            [distribution("scitex-owner", ["not a requirement !"])]
        )


def test_explicit_docker_and_toolchain_roots_remain_declared():
    roots, _ = COLLECTOR.resolution_inputs([distribution("scitex-owner")])
    assert {
        "daphne",
        "psycopg2-binary",
        "openalex-local",
        "crossref-local",
        "pip",
        "setuptools",
        "wheel",
        "scitex-writer",
        "figrecipe",
    } <= set(roots)


def test_root_input_does_not_allow_arbitrary_url_admission():
    with pytest.raises(ValueError, match="index requirements"):
        COLLECTOR.resolution_inputs(
            [distribution("scitex-owner")],
            explicit_roots=["outside @ https://example.invalid/private.whl"],
        )


def test_docker_compiles_then_syncs_without_disabling_late_gates():
    text = (ROOT / "deployment/docker/docker_prod/Dockerfile.prod").read_text()
    collect = text.index("RUN python scripts/deploy/installed_runtime_roots.py")
    compile_at = text.index("uv pip compile", collect)
    sync = text.index("uv pip sync --system", compile_at)
    check = text.index("uv pip check --system", sync)
    assert (
        collect
        < compile_at
        < sync
        < check
        < text.rindex("verify_image_dependency_contract.py")
    )


def owned_commands(tmp_path):
    uv = shutil.which("uv")
    assert uv
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    environment = tmp_path / "env"
    subprocess.run(
        [uv, "venv", "--python", sys.executable, str(environment)],
        check=True,
        capture_output=True,
    )
    python = str(environment / "bin/python")
    common = ["--python", python, "--no-index", "--find-links", str(wheelhouse)]

    def run(*args, check=True):
        return subprocess.run(
            args, cwd=tmp_path, capture_output=True, text=True, check=check
        )

    def installed():
        site = (
            environment
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )
        return list(metadata.distributions(path=[site]))

    return uv, wheelhouse, python, common, run, installed


def test_normal_sync_removes_only_orphan_and_preserves_optional_heavy_capability(
    tmp_path,
):
    uv, wheels, python, common, run, installed = owned_commands(tmp_path)
    wheel(wheels, "owned-core", "1.0")
    wheel(wheels, "owned-core", "2.0")
    wheel(wheels, "owned-protocol", "3.0")
    wheel(wheels, "owned-protocol", "4.0", ["owned-obsolete-helper>=2"])
    wheel(wheels, "owned-obsolete-helper", "2.0", ["owned-core>=2"])
    wheel(wheels, "owned-heavy", "1.0")
    wheel(wheels, "owned-heavy", "2.0")
    wheel(
        wheels,
        "scitex-owned-capability",
        "1.0",
        ["owned-core<2", "owned-protocol<4", "owned-heavy; extra == 'scientific'"],
        extras=["scientific"],
    )
    run(uv, "pip", "install", *common, "owned-protocol==4.0", "owned-heavy==1.0")
    run(uv, "pip", "install", *common, "scitex-owned-capability==1.0")
    assert run(uv, "pip", "check", "--python", python, check=False).returncode != 0
    roots, lock = tmp_path / "roots.in", tmp_path / "runtime.lock"
    COLLECTOR.write_inputs(
        roots, lock, installed(), explicit_roots=(), local_project=None
    )
    assert "owned-obsolete-helper==2.0" in lock.read_text()
    run(
        uv,
        "pip",
        "compile",
        "--no-index",
        "--find-links",
        str(wheels),
        str(roots),
        "-o",
        str(lock),
    )
    run(uv, "pip", "sync", *common, str(lock))
    assert (
        run(uv, "pip", "check", "--python", python).returncode,
        {d.metadata["Name"]: d.version for d in installed()},
    ) == (
        0,
        {
            "owned-core": "1.0",
            "owned-protocol": "3.0",
            "owned-heavy": "1.0",
            "scitex-owned-capability": "1.0",
        },
    )


def test_real_required_conflict_refuses_without_changing_installed_packages(tmp_path):
    uv, wheels, python, common, run, installed = owned_commands(tmp_path)
    wheel(wheels, "owned-core", "1.0")
    wheel(wheels, "owned-core", "2.0")
    wheel(wheels, "scitex-required-one", "1.0", ["owned-core<2"])
    wheel(wheels, "scitex-required-two", "1.0", ["owned-core>=2"])
    run(uv, "pip", "install", *common, "scitex-required-one==1.0")
    run(uv, "pip", "install", *common, "scitex-required-two==1.0")
    before = {d.metadata["Name"]: d.version for d in installed()}
    roots, lock = tmp_path / "roots.in", tmp_path / "runtime.lock"
    COLLECTOR.write_inputs(
        roots, lock, installed(), explicit_roots=(), local_project=None
    )
    result = run(
        uv,
        "pip",
        "compile",
        "--no-index",
        "--find-links",
        str(wheels),
        str(roots),
        "-o",
        str(lock),
        check=False,
    )
    assert (
        result.returncode != 0,
        {d.metadata["Name"]: d.version for d in installed()},
    ) == (True, before)


def test_manifest_preserves_seed_and_verifies_retained_capabilities(tmp_path):
    roots, lock = tmp_path / "roots.in", tmp_path / "runtime.lock"
    installed = [
        distribution("scitex-owner", ["owned-heavy"]),
        distribution("owned-heavy"),
        distribution("old-orphan"),
    ]
    COLLECTOR.write_inputs(
        roots, lock, installed, explicit_roots=(), local_project=None
    )
    initial = json.loads(roots.with_suffix(".manifest.json").read_text())
    seed = lock.with_suffix(".cached-preferences.in").read_text()
    lock.write_text("scitex-owner==1.0\nowned-heavy==1.0\n")
    verified = COLLECTOR.verify_closure(
        roots.with_suffix(".manifest.json"), installed[:2]
    )
    assert (
        initial["baseline_versions"],
        "old-orphan==1.0" in seed,
        verified["removed_cached_packages"],
        verified["retained_capabilities_verified"],
    ) == (
        {"scitex-owner": "1.0", "owned-heavy": "1.0", "old-orphan": "1.0"},
        True,
        ["old-orphan"],
        True,
    )


def test_manifest_refuses_missing_retained_capability_without_claiming_success(
    tmp_path,
):
    roots, lock = tmp_path / "roots.in", tmp_path / "runtime.lock"
    installed = [
        distribution("scitex-owner", ["owned-heavy"]),
        distribution("owned-heavy"),
    ]
    COLLECTOR.write_inputs(
        roots, lock, installed, explicit_roots=(), local_project=None
    )
    manifest = roots.with_suffix(".manifest.json")
    before = manifest.read_bytes()
    with pytest.raises(ValueError, match="lost retained capabilities"):
        COLLECTOR.verify_closure(manifest, installed[:1])
    assert manifest.read_bytes() == before
