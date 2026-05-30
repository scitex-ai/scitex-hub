"""scitex_cloud -> scitex_hub deprecation-shim contract.

``scitex-cloud`` is the OLD name of ``scitex-hub`` (ADR-0001). The Phase-1
rename keeps ``import scitex_cloud`` working as a thin compatibility shim that
re-exports from :mod:`scitex_hub` and emits a :class:`DeprecationWarning`.

Each check runs in a fresh subprocess so the shim's import-time side effects
(the warning, the meta-path finder) are observed cleanly regardless of what
the parent test session already imported.
"""

import subprocess
import sys
import textwrap


def _run_snippet_ok(snippet: str) -> bool:
    """Run ``snippet`` in a child interpreter; True iff it prints ``OK``."""
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(snippet)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode == 0 and "OK" in result.stdout


def test_importing_scitex_cloud_emits_deprecation_warning():
    # Arrange
    snippet = """
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import scitex_cloud  # noqa: F401
        cats = [w.category for w in caught]
        assert any(issubclass(c, DeprecationWarning) for c in cats), cats
        print("OK")
    """
    # Act
    ok = _run_snippet_ok(snippet)
    # Assert
    assert ok


def test_scitex_cloud_top_level_symbols_alias_scitex_hub():
    # Arrange
    snippet = """
        import warnings
        warnings.simplefilter("ignore")
        import scitex_cloud, scitex_hub
        assert scitex_cloud.CloudClient is scitex_hub.CloudClient
        assert scitex_cloud.__version__ == scitex_hub.__version__
        print("OK")
    """
    # Act
    ok = _run_snippet_ok(snippet)
    # Assert
    assert ok


def test_scitex_cloud_submodules_are_identical_to_scitex_hub():
    # Arrange
    snippet = """
        import warnings
        warnings.simplefilter("ignore")
        import scitex_cloud.sdk, scitex_hub.sdk
        import scitex_cloud.module, scitex_hub.module
        from scitex_cloud.module import _decorator as c_dec
        import scitex_hub.module._decorator as h_dec
        assert scitex_cloud.sdk is scitex_hub.sdk
        assert scitex_cloud.module is scitex_hub.module
        assert c_dec is h_dec
        print("OK")
    """
    # Act
    ok = _run_snippet_ok(snippet)
    # Assert
    assert ok
