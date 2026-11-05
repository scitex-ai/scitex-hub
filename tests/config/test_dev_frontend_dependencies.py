"""Exercise development dependency startup with real offline npm packages."""

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _workspace(tmp_path, available):
    app = tmp_path / "app"
    app.mkdir()
    (app / "node_modules").mkdir()
    (app / "logs").mkdir()
    script_dir = app / "scripts/deploy"
    script_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts/deploy/install_dev_frontend.sh", script_dir)
    shutil.copy2(ROOT / "scripts/deploy/install_dev_frontend.py", script_dir)
    package = {
        "name": "frontend-startup-fixture",
        "version": "1.0.0",
        "private": True,
        "dependencies": {"@scitex-fixture/local": "file:../peer"},
        "scripts": {
            "build": "node -e \"const v=require('@scitex-fixture/local');require('fs').writeFileSync('built.txt',v)\""
        },
    }
    (app / "package.json").write_text(json.dumps(package))
    if available:
        peer = tmp_path / "peer"
        peer.mkdir()
        (peer / "package.json").write_text(
            json.dumps(
                {
                    "name": "@scitex-fixture/local",
                    "version": "1.0.0",
                    "main": "index.js",
                }
            )
        )
        (peer / "index.js").write_text('module.exports = "local dependency ready";\n')
    return app


def _start(app):
    source = (ROOT / "deployment/docker/docker_dev/entrypoint.sh").read_text()
    function = (
        "start_platform_vite() {"
        + source.split("start_platform_vite() {", 1)[1].split("\n}\n", 1)[0]
        + "\n}\n"
    )
    # Map the component's fixed container root onto this owned filesystem.
    function = function.replace("/app", str(app))
    logging = (ROOT / "deployment/docker/common/lib/logging.src").read_text()
    logging = logging.replace("/app", str(app))
    program = "set -e\n" + logging + "\n" + function + "\nstart_platform_vite\n"
    env = os.environ.copy()
    env.update(
        SCITEX_HUB_VITE_USE_BUILD="true",
        NPM_CONFIG_OFFLINE="true",
        NPM_CONFIG_CACHE=str(app / "npm-cache"),
        NPM_CONFIG_USERCONFIG="/dev/null",
        HOME=str(app / "home"),
    )
    return subprocess.run(
        ["bash", "-c", program], env=env, capture_output=True, text=True
    )


def test_existing_node_modules_does_not_skip_required_workspace_dependencies(tmp_path):
    # Arrange
    app = _workspace(tmp_path, available=True)
    # Act
    result = _start(app)
    # Assert
    assert (
        result.returncode,
        (app / "built.txt").read_text() if (app / "built.txt").exists() else None,
    ) == (0, "local dependency ready"), (
        result.stdout + result.stderr
    )


def test_missing_workspace_dependency_stops_startup_instead_of_serving_stale_assets(
    tmp_path,
):
    # Arrange
    app = _workspace(tmp_path, available=False)
    # Act
    result = _start(app)
    # Assert
    assert result.returncode != 0 and not (app / "built.txt").exists()


def test_failed_bundle_build_stops_startup_and_retains_previous_manifest(tmp_path):
    # Arrange
    app = _workspace(tmp_path, available=True)
    package = json.loads((app / "package.json").read_text())
    package["scripts"]["build"] = 'node -e "process.exit(17)"'
    (app / "package.json").write_text(json.dumps(package))
    manifest = app / "staticfiles/vite/.vite/manifest.json"
    manifest.parent.mkdir(parents=True)
    retained = '{"old":{"file":"assets/old.js","isEntry":true}}'
    manifest.write_text(retained)
    # Act
    result = _start(app)
    # Assert
    assert result.returncode != 0 and manifest.read_text() == retained


def test_linked_frontend_provider_installs_its_own_local_dependency_graph(tmp_path):
    # Arrange
    app = _workspace(tmp_path, available=True)
    peer = tmp_path / "peer"
    package = json.loads((peer / "package.json").read_text())
    package["dependencies"] = {"@scitex-fixture/child": "file:../child"}
    (peer / "package.json").write_text(json.dumps(package))
    (peer / "index.js").write_text(
        "module.exports = require('@scitex-fixture/child');\n"
    )
    child = tmp_path / "child"
    child.mkdir()
    (child / "package.json").write_text(
        json.dumps(
            {
                "name": "@scitex-fixture/child",
                "version": "1.0.0",
                "main": "index.js",
            }
        )
    )
    (child / "index.js").write_text('module.exports = "local dependency ready";\n')
    # Act
    result = _start(app)
    # Assert
    assert (
        result.returncode,
        (app / "built.txt").read_text() if (app / "built.txt").exists() else None,
    ) == (0, "local dependency ready"), (
        result.stdout + result.stderr
    )
