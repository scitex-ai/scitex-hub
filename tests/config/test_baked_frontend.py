"""Real Git/file/SDK-namespace controls for the baked-frontend protocol.

The small JS files model an owned closure, not a claimed production Vite build.
The production Docker RUN executes the real complete npm/Vite build before seal.
"""

import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("mode", ["baked", "build"])
def test_real_boot_cleanup_preserves_baked_chunks_and_cleans_legacy_build(
    mode, tmp_path
):
    source = (ROOT / "deployment/docker/common/scripts/root-init.sh").read_text()
    function = re.search(
        r"^prepare_vite_static_directory\(\) \{\n.*?^\}", source, re.M | re.S
    ).group()
    assert "prepare_vite_static_directory /app/staticfiles/vite" in source
    vite = tmp_path / "vite"
    (vite / ".vite").mkdir(parents=True)
    (vite / ".vite/manifest.json").write_bytes(b'{"existing":"old-chunk.js"}')
    (vite / "old-chunk.js").write_bytes(b"existing open page")
    before = {
        str(p.relative_to(vite)): p.read_bytes()
        for p in vite.rglob("*")
        if p.is_file()
    }
    subprocess.run(
        [
            "bash", "-c", function + '\nprepare_vite_static_directory "$1"',
            "boot-test", str(vite),
        ],
        env={
            "PATH": os.environ.get("PATH", os.defpath),
            "SCITEX_HUB_FRONTEND_MODE": mode,
        },
        check=True,
        capture_output=True,
        timeout=10,
    )
    after = {
        str(p.relative_to(vite)): p.read_bytes()
        for p in vite.rglob("*")
        if p.is_file()
    }
    assert (vite.exists(), after) == ((True, before) if mode == "baked" else (False, {}))


def load(name):
    path = ROOT / "scripts/deploy" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ARTIFACT = load("_frontend_artifact")
SOURCES = load("_frontend_sources")


@pytest.fixture
def prepared(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    for name, content in {
        "pyproject.toml": '[project]\nname="scitex-hub"\nversion="0.22.0a0"\n',
        "package.json": '{"name":"owned-frontend"}',
        "package-lock.json": '{"lockfileVersion":3}',
        "vite.config.ts": "export default {};",
        "vite.entries.ts": "export const entries = {};",
        ".scitex-apps.json": '{"apps":[]}',
    }.items():
        (app / name).write_text(content)
    vite = app / "staticfiles/vite"
    (vite / "assets").mkdir(parents=True)
    (vite / ".vite").mkdir()
    for name, content in {
        "entry-a1.js": "export const value=1;",
        "chunk-b2.js": "export const lazy=2;",
        "style-c3.css": "body{color:inherit}",
    }.items():
        (vite / "assets" / name).write_text(content)
    manifest = {
        "entry.ts": {
            "file": "assets/entry-a1.js",
            "css": ["assets/style-c3.css"],
            "dynamicImports": ["_chunk"],
        },
        "_chunk": {"file": "assets/chunk-b2.js"},
    }
    (vite / ".vite/manifest.json").write_text(json.dumps(manifest))
    sdk = ARTIFACT.sdk_namespace()
    inputs = {
        "sdk": {
            "version": metadata.version("scitex-sdk"),
            "namespace_sha256": hashlib.sha256(
                json.dumps(sdk, sort_keys=True).encode()
            ).hexdigest(),
        },
        "sources": [],
        "peers": [],
        "python_versions": {
            dist.metadata["Name"]: dist.version for dist in metadata.distributions()
        },
    }
    artifact = tmp_path / "artifact"
    ARTIFACT.seal(app, vite, artifact, inputs)
    return app, artifact, tmp_path / "served"


def test_verified_complete_closure_installs_and_preserves_old_hashed_chunks(prepared):
    app, artifact, target = prepared
    (target / "assets").mkdir(parents=True)
    old = target / "assets/previous-deadbeef.js"
    old.write_text("previous release")
    receipt = ARTIFACT.install(artifact, app, target)
    assert old.read_text() == "previous release"
    assert all(
        ARTIFACT.digest(target / name) == value
        for name, value in receipt["files"].items()
    )
    assert ARTIFACT.install(artifact, app, target) == receipt


@pytest.mark.parametrize(
    "change",
    [
        "tamper",
        "partial",
        "extra",
        "missing_receipt",
        "lock",
        "source",
        "sdk_metadata",
        "build_helper",
    ],
)
def test_invalid_artifact_never_changes_current_manifest(prepared, change):
    app, artifact, target = prepared
    (target / ".vite").mkdir(parents=True)
    current = target / ".vite/manifest.json"
    current.write_text("previous manifest")
    if change == "tamper":
        (artifact / "vite/assets/entry-a1.js").write_text("modified")
    elif change == "partial":
        (artifact / "vite/assets/chunk-b2.js").unlink()
    elif change == "extra":
        (artifact / "vite/assets/unexpected.js").write_text("extra")
    elif change == "missing_receipt":
        (artifact / "receipt.json").unlink()
    elif change == "lock":
        (app / "package-lock.json").write_text("changed")
    elif change == "source":
        (app / "vite.entries.ts").write_text("changed")
    elif change == "build_helper":
        (app / "vite.monaco-sanitizer.ts").write_text("changed boundary")
    else:
        path = artifact / "receipt.json"
        data = json.loads(path.read_text())
        data["inputs"]["sdk"]["version"] = "0.0.0"
        path.write_text(json.dumps(data))
    with pytest.raises((ValueError, FileNotFoundError)):
        ARTIFACT.install(artifact, app, target)
    assert current.read_text() == "previous manifest"


def test_symbolic_artifact_and_destination_members_are_refused(prepared, tmp_path):
    app, artifact, target = prepared
    target.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (target / "assets").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic"):
        ARTIFACT.install(artifact, app, target)
    assert not list(outside.iterdir())


def test_referenced_but_absent_chunk_is_not_a_complete_build(prepared):
    app, artifact, _ = prepared
    root = artifact / "vite"
    manifest = json.loads((root / ".vite/manifest.json").read_text())
    manifest["entry.ts"]["dynamicImports"] = ["absent"]
    (root / ".vite/manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="absent chunk"):
        ARTIFACT.validate_manifest(root, ARTIFACT.files(root))


@pytest.fixture
def release_repo(tmp_path):
    repo = tmp_path / "upstream"
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "tag.gpgsign=false",
                "-c",
                "user.name=Owned Test",
                "-c",
                "user.email=owned@example.invalid",
                *args,
            ],
            cwd=repo,
            text=True,
        ).strip()

    git("init", "--initial-branch=main")
    (repo / "pyproject.toml").write_text(
        '[project]\nname="owned-frontend"\nversion="1.2.3"\n'
    )
    git("add", "pyproject.toml")
    git("commit", "-m", "Owned release")
    git("tag", "v1.2.3")
    return repo, git


def test_real_tag_and_source_identity_are_verified_before_use(release_repo, tmp_path):
    repo, git = release_repo
    result = SOURCES.clone_release(
        str(repo), "v1.2.3", tmp_path / "checkout", "owned-frontend", "1.2.3"
    )
    assert result["commit"] == git("rev-parse", "HEAD")
    assert result["tag"] == "v1.2.3"


def test_tag_with_wrong_source_version_is_refused(release_repo, tmp_path):
    repo, _ = release_repo
    with pytest.raises(ValueError, match="source version"):
        SOURCES.clone_release(
            str(repo), "v1.2.3", tmp_path / "wrong", "owned-frontend", "1.2.4"
        )


def test_existing_checkout_is_never_overwritten(release_repo):
    repo, _ = release_repo
    before = (repo / "pyproject.toml").read_bytes()
    with pytest.raises(ValueError, match="existing"):
        SOURCES.clone_release(str(repo), "v1.2.3", repo, "owned-frontend", "1.2.3")
    assert (repo / "pyproject.toml").read_bytes() == before


@pytest.mark.parametrize("source_first", [True, False])
def test_editable_origin_cannot_hide_behind_source_or_wheel_metadata(
    tmp_path, monkeypatch, source_first
):
    # Reproduce the actual PEP 660 dual-record discovery with real stdlib
    # metadata, independently of how the test runner installed Hub itself.
    source = tmp_path / "source"
    installed = tmp_path / "installed"
    source.mkdir()
    installed.mkdir()
    package = "owned_frontend"
    contents = "Metadata-Version: 2.1\nName: owned-frontend\nVersion: 1.2.3\n"
    egg = source / f"{package}.egg-info"
    egg.mkdir()
    (egg / "PKG-INFO").write_text(contents)
    wheel = installed / f"{package}-1.2.3.dist-info"
    wheel.mkdir()
    (wheel / "METADATA").write_text(contents)
    (wheel / "WHEEL").write_text("Wheel-Version: 1.0\nTag: py3-none-any\n")
    (wheel / "direct_url.json").write_text(
        json.dumps({"url": source.as_uri(), "dir_info": {"editable": True}})
    )
    for path in (installed, source) if source_first else (source, installed):
        monkeypatch.syspath_prepend(str(path))
    selected = metadata.distribution("owned-frontend")
    assert bool(selected.read_text("WHEEL")) is not source_first
    assert len(list(metadata.distributions(name="owned-frontend"))) == 2
    with pytest.raises(ValueError, match="installed wheels"):
        SOURCES.installed_release("owned-frontend")


def test_file_dependencies_bind_to_the_actual_wheel_provider(tmp_path):
    source = SOURCES.installed_npm_package("scitex-sdk")
    package = tmp_path / "package.json"
    package.write_text(
        json.dumps({"dependencies": {"@scitex/sdk": "file:../unreviewed"}})
    )
    result = SOURCES.bind_file_dependencies(package, {"@scitex/sdk": source})
    value = json.loads(package.read_text())["dependencies"]["@scitex/sdk"]
    assert (tmp_path / value.removeprefix("file:")).resolve() == source
    assert result["before_sha256"] != result["after_sha256"]


def test_unknown_local_npm_provider_is_not_followed(tmp_path):
    package = tmp_path / "package.json"
    package.write_text('{"dependencies":{"unknown":"file:/private"}}')
    before = package.read_bytes()
    with pytest.raises(ValueError, match="Unproven"):
        SOURCES.bind_file_dependencies(package, {})
    assert package.read_bytes() == before


@pytest.mark.parametrize(
    "mode,python_mode,status",
    [
        ("build", "editable", 0),
        ("baked", "image-only", 0),
        ("baked", "editable", 2),
        ("unknown", "image-only", 2),
    ],
)
def test_real_mode_block_fails_closed_without_build_fallback(mode, python_mode, status):
    source = (ROOT / "deployment/docker/common/scripts/entrypoint-prod.sh").read_text()
    block = source.split("# BEGIN FRONTEND MODE VALIDATION", 1)[1].split(
        "# END FRONTEND MODE VALIDATION", 1
    )[0]
    library = ROOT / "deployment/docker/common/lib/logging.src"
    result = subprocess.run(
        ["bash", "-c", 'source "$1"; ' + block, "bash", str(library)],
        env={
            "PATH": "/usr/bin:/bin",
            "SCITEX_HUB_FRONTEND_MODE": mode,
            "SCITEX_APPS_PYTHON_MODE": python_mode,
        },
        capture_output=True,
    )
    assert result.returncode == status


def test_cold_docker_build_prepares_sources_before_npm_and_protects_runtime_tools():
    docker = (ROOT / "deployment/docker/docker_prod/Dockerfile.prod").read_text()
    source = (ROOT / "deployment/docker/common/scripts/entrypoint-prod.sh").read_text()
    assert "COPY --chown=scitex:scitex package.json ./\nRUN" not in docker
    assert docker.index("COPY --chown=scitex:scitex . .") < docker.index(
        "python scripts/deploy/bake_frontend.py"
    )
    assert docker.index('"crossref-local"') < docker.index(
        "python scripts/deploy/bake_frontend.py"
    )
    assert (
        "COPY --chmod=644 scripts/deploy/_frontend_artifact.py /opt/scitex-frontend-tools/"
        in docker
    )
    baked = source.split('if [ "$FRONTEND_MODE" = baked ]; then', 1)[1].split(
        "else", 1
    )[0]
    assert "python /opt/scitex-frontend-tools/_frontend_artifact.py" in baked
    assert "npm " not in baked and "install_apps.sh" not in baked
    assert source.index("collect_static_files") < source.index(
        "python /opt/scitex-frontend-tools/_frontend_artifact.py"
    )


def test_app_like_sibling_and_bridge_layout_resolves_only_verified_providers(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    ui = tmp_path / "scitex-ui"
    ui.mkdir()
    (ui / "package.json").write_text('{"name":"@scitex/ui"}')
    fig = tmp_path / "figrecipe"
    declaration = fig / "src/figrecipe/_django/manifest.json"
    frontend = declaration.parent / "frontend"
    (frontend / "src").mkdir(parents=True)
    (frontend / "src/workspace.ts").write_text("export {};")
    declaration.write_text('{"bridge":{"entry":"src/workspace.ts"}}')
    (frontend / "package.json").write_text('{"name":"figrecipe-editor"}')
    (app / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "@scitex/ui": "file:../scitex-ui",
                    "figrecipe-editor": "file:../figrecipe/src/figrecipe/_django/frontend",
                }
            }
        )
    )
    manifests, providers = SOURCES.npm_inputs(
        app,
        {
            "sources": [{"distribution": "scitex-ui"}, {"distribution": "figrecipe"}],
            "peers": [],
        },
    )
    assert set(manifests) == {
        app / "package.json",
        ui / "package.json",
        frontend / "package.json",
    }
    SOURCES.bind_file_dependencies(app / "package.json", providers)
    for name, value in json.loads((app / "package.json").read_text())[
        "dependencies"
    ].items():
        target = (app / value.removeprefix("file:")).resolve()
        assert target == providers[name].resolve()
        assert json.loads((target / "package.json").read_text())["name"] == name


def test_real_npm_stale_local_link_is_replaced_by_admitted_provider(tmp_path):
    old = tmp_path / "old-provider"
    new = tmp_path / "verified-provider"
    package = tmp_path / "app"
    for path, value in ((old, "old"), (new, "admitted")):
        path.mkdir()
        (path / "package.json").write_text(
            '{"name":"owned-port","version":"1.0.0","main":"index.js"}'
        )
        (path / "index.js").write_text("module.exports=" + json.dumps(value))
    package.mkdir()
    manifest = package / "package.json"
    manifest.write_text(
        '{"name":"owned-consumer","version":"1.0.0","dependencies":{"owned-port":"file:../old-provider"}}'
    )
    env = {
        # Keep the declared runner toolchain (setup-node uses its own prefix).
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": os.environ["HOME"],
        "NPM_CONFIG_GLOBALCONFIG": str(tmp_path / "global-npmrc"),
        "NPM_CONFIG_CACHE": str(tmp_path / "cache"),
        "NPM_CONFIG_USERCONFIG": str(tmp_path / "npmrc"),
    }
    (tmp_path / "npmrc").touch()
    (tmp_path / "global-npmrc").touch()
    command = [
        "npm",
        "install",
        "--package-lock-only",
        "--offline",
        "--no-audit",
        "--no-fund",
    ]
    subprocess.run(
        command, cwd=package, env=env, check=True, capture_output=True, timeout=30
    )
    before = (package / "package-lock.json").read_bytes()
    old.rename(tmp_path / "removed-provider")
    witness = SOURCES.bind_file_dependencies(manifest, {"owned-port": new})
    assert witness["original_lock_sha256"] == hashlib.sha256(before).hexdigest()
    assert not (package / "package-lock.json").exists()
    subprocess.run(
        command, cwd=package, env=env, check=True, capture_output=True, timeout=30
    )
    subprocess.run(
        ["npm", "ci", "--offline", "--no-audit", "--no-fund"],
        cwd=package,
        env=env,
        check=True,
        capture_output=True,
        timeout=30,
    )
    result = subprocess.run(
        ["node", "-e", "process.stdout.write(require('owned-port'))"],
        cwd=package,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.stdout == "admitted"
    assert "old-provider" not in (package / "package-lock.json").read_text()
