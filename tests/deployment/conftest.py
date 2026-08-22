#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real target environments for the deploy preflight's tests.

Every scenario built here is a genuine environment, never a mock: a directory of
real ``.dist-info`` metadata and real importable modules, placed on a separate
interpreter's ``sys.path`` and interrogated through the same runner code path the
production deploy uses. The only thing that differs between these runs and the
prod call is the ``--target`` string.

That matters more than usual here. The thing under test is a gate whose entire
value is its ability to go RED on a real environment; a mocked lookup would prove
the mock works and nothing whatever about the gate. Both of the outages this gate
exists to stop got past checks that were technically present.

Each scenario runs ONCE at session scope and is asserted by several
single-assertion tests, so a failure names the exact property that broke rather
than the first line of a long test.
"""

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEPLOY = REPO_ROOT / "scripts" / "deploy"
DRIVER = DEPLOY / "preflight_sibling_floors.py"
PROBE = DEPLOY / "preflight_probe.py"
CONTRACT = DEPLOY / "preflight_contract.json"

#: An umbrella that imports fine and raises only when an attribute is touched --
#: the shape ``scitex/__init__.py`` uses for its ``_LazyModule`` entries, and the
#: reason probing the import alone is not enough.
LAZY_UMBRELLA = (
    "def __getattr__(name):\n"
    "    if name == 'plt':\n"
    "        raise ImportError('demosib_plt is required for demosib_umbrella.plt')\n"
    "    raise AttributeError(name)\n"
)

WRITER_SOURCES = {"apps/demo/urls.py": "from demosib_writer.workspace_layout import compile_script\n"}
#: 2.41.0 imports perfectly well. It merely lacks the symbol 2.42.0 added -- which
#: is exactly why the floor half is needed and the import half is not sufficient.
WRITER_MODULES = {
    "demosib_writer/__init__.py": "",
    "demosib_writer/workspace_layout.py": "compile_script = None\n",
}

UMBRELLA_SOURCES = {"apps/demo/plot.py": "import demosib_umbrella\n"}
UMBRELLA_PROBE = [{
    "module": "demosib_umbrella.io", "attrs": [],
    "why": "the lazy submodule the outage touched",
}]


def load_deploy_module(name):
    """Import one of the preflight's modules from scripts/, which is not a package."""
    spec = importlib.util.spec_from_file_location(name, DEPLOY / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _install(site, distribution, version, modules=None):
    """Genuine dist-info metadata plus genuine importable modules.

    ``importlib.metadata.version()`` inside the target reads this exactly as it
    reads a pip install.
    """
    info = site / "{0}-{1}.dist-info".format(distribution.replace("-", "_"), version)
    info.mkdir(parents=True, exist_ok=True)
    _write(
        info / "METADATA",
        "Metadata-Version: 2.1\nName: {0}\nVersion: {1}\n".format(distribution, version),
    )
    for module_path, source in (modules or {}).items():
        _write(site / module_path, source)


def _build(root, dependencies, sources, probes=()):
    """A repo that DECLARES floors, and a separate environment that HAS versions."""
    repo, site = root / "repo", root / "site"
    site.mkdir(parents=True, exist_ok=True)

    body = "".join('    "{0}",\n'.format(d) for d in dependencies)
    _write(
        repo / "pyproject.toml",
        '[project]\nname = "demo-hub"\nversion = "0.0.1"\n'
        "dependencies = [\n{0}]\n\n"
        "[project.optional-dependencies]\nall = [\n{1}]\n".format(body, body),
    )
    for relative, source in sources.items():
        _write(repo / relative, source)
    (repo / "config").mkdir(exist_ok=True)
    (repo / "src").mkdir(exist_ok=True)

    contract_path = root / "contract.json"
    _write(contract_path, json.dumps({
        "sibling_distribution_prefixes": ["demosib-"],
        "sibling_distributions": [],
        "ignore_distributions": [],
        "sibling_import_roots": [],
        "sibling_import_root_prefixes": ["demosib_", "demosib."],
        "ignore_import_roots": [],
        "scan_dirs": ["apps", "config", "src"],
        "prod_image_extras": ["all"],
        "extra_import_probes": list(probes),
    }, indent=2))

    runner = root / "runner.sh"
    _write(
        runner,
        "#!/bin/sh\n# Executes the probe INSIDE the constructed target environment.\n"
        'PYTHONPATH="{0}" exec "{1}" -\n'.format(site, sys.executable),
    )
    runner.chmod(0o755)
    return repo, site, contract_path, runner


def _drive(repo, contract_path, target):
    completed = subprocess.run(
        [
            sys.executable, str(DRIVER),
            "--target", target,
            "--pyproject", str(repo / "pyproject.toml"),
            "--repo-root", str(repo),
            "--contract", str(contract_path),
        ],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300,
        env=dict(os.environ, NO_COLOR="1"),
    )
    return completed.returncode, completed.stdout.decode("utf-8", "replace")


def _scenario(root, dependencies, sources, installs, probes=()):
    repo, site, contract_path, runner = _build(root, dependencies, sources, probes)
    for distribution, version, modules in installs:
        _install(site, distribution, version, modules)
    return _drive(repo, contract_path, "cmd:/bin/sh {0}".format(runner))


def _umbrella_modules(with_transitive):
    modules = {
        "demosib_umbrella/__init__.py": "VERSION = '1.0.0'\n",
        # The umbrella imports a package that NOTHING declares. This is the
        # 2026-08-22 chain: scitex.io -> scitex.decorators -> scitex_decorators,
        # undeclared by hub, by scitex, and by scitex-io alike.
        "demosib_umbrella/io.py": "import demosib_hidden_dep\n",
    }
    if with_transitive:
        modules["demosib_hidden_dep/__init__.py"] = "OK = True\n"
    return modules


@pytest.fixture(scope="session")
def preflight_declarations():
    return load_deploy_module("preflight_declarations")


@pytest.fixture(scope="session")
def preflight_versions():
    return load_deploy_module("preflight_versions")


@pytest.fixture(scope="session")
def preflight_probe_path():
    return PROBE


@pytest.fixture(scope="session")
def hub_pyproject():
    return REPO_ROOT / "pyproject.toml"


@pytest.fixture(scope="session")
def real_repo_scan(preflight_declarations):
    """The AST scan run against hub's own source, with the shipped contract."""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return preflight_declarations.module_scope_sibling_imports(REPO_ROOT, contract)


@pytest.fixture(scope="session")
def harness_control(tmp_path_factory):
    """One GREEN through the identical path, so a red is not just a broken harness."""
    return _scenario(
        tmp_path_factory.mktemp("control"),
        ["demosib-writer>=2.42.0"],
        {"apps/demo/urls.py": "import demosib_writer\n"},
        [("demosib-writer", "2.42.0", {"demosib_writer/__init__.py": "VALUE = 1\n"})],
    )


@pytest.fixture(scope="session")
def below_floor(tmp_path_factory):
    """The 2026-08-18 shape: declared >=2.42.0, target holds 2.41.0."""
    return _scenario(
        tmp_path_factory.mktemp("below"), ["demosib-writer>=2.42.0"], WRITER_SOURCES,
        [("demosib-writer", "2.41.0", WRITER_MODULES)],
    )


@pytest.fixture(scope="session")
def at_floor(tmp_path_factory):
    """The same fixture with the one version changed -- the green pole."""
    return _scenario(
        tmp_path_factory.mktemp("at"), ["demosib-writer>=2.42.0"], WRITER_SOURCES,
        [("demosib-writer", "2.42.0", WRITER_MODULES)],
    )


@pytest.fixture(scope="session")
def undeclared_absent(tmp_path_factory):
    """The 2026-08-22 shape: an undeclared transitive dependency is missing."""
    return _scenario(
        tmp_path_factory.mktemp("hidden_absent"), ["demosib-umbrella>=1.0.0"], UMBRELLA_SOURCES,
        [("demosib-umbrella", "1.0.0", _umbrella_modules(False))], UMBRELLA_PROBE,
    )


@pytest.fixture(scope="session")
def undeclared_present(tmp_path_factory):
    return _scenario(
        tmp_path_factory.mktemp("hidden_present"), ["demosib-umbrella>=1.0.0"], UMBRELLA_SOURCES,
        [("demosib-umbrella", "1.0.0", _umbrella_modules(True))], UMBRELLA_PROBE,
    )


@pytest.fixture(scope="session")
def lazy_attribute(tmp_path_factory):
    """An umbrella that imports cleanly and raises only on attribute access."""
    return _scenario(
        tmp_path_factory.mktemp("lazy"),
        ["demosib-umbrella>=1.0.0"],
        {"apps/demo/plot.py": "# the real import is at FUNCTION scope, invisible to an AST scan\n"},
        [("demosib-umbrella", "1.0.0", {"demosib_umbrella/__init__.py": LAZY_UMBRELLA})],
        [{"module": "demosib_umbrella", "attrs": ["plt"], "why": "the lazy attribute"}],
    )


@pytest.fixture(scope="session")
def unreachable_target(tmp_path_factory):
    root = tmp_path_factory.mktemp("unreachable")
    repo, _site, contract_path, _runner = _build(
        root, ["demosib-writer>=1.0"], {"apps/demo/x.py": "\n"}
    )
    return _drive(repo, contract_path, "cmd:{0}".format(root / "there-is-no-such-runner"))


@pytest.fixture(scope="session")
def local_target_run():
    """``--target local`` against the real repo, to check it disowns its own result."""
    completed = subprocess.run(
        [sys.executable, str(DRIVER), "--target", "local"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=300, env=dict(os.environ, NO_COLOR="1"),
    )
    return completed.returncode, completed.stdout.decode("utf-8", "replace")

# EOF
