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


def test_deprecation_message_names_new_module_and_adr():
    """The operator-facing migration hint must point at the new name AND the ADR.

    Without these two strings the user is told "deprecated" with no way to
    find the replacement or the rationale — silent migration handoff is
    the failure mode this test prevents.
    """
    # Arrange
    snippet = """
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import scitex_cloud  # noqa: F401
        dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert dep, "no DeprecationWarning captured"
        msg = str(dep[0].message)
        assert "scitex_hub" in msg, f"replacement name missing in {msg!r}"
        assert "0001" in msg, f"ADR-0001 link missing in {msg!r}"
        print("OK")
    """
    # Act
    ok = _run_snippet_ok(snippet)
    # Assert
    assert ok


def test_unknown_attribute_on_shim_raises_attribute_error():
    """PEP-562 ``__getattr__`` must not silently swallow lookup misses.

    If the fallback silently returns ``None`` (or worse, an unrelated
    object), downstream code reading the legacy name observes a fake
    success — exactly the silent-fallback failure mode the rename ADR
    rejects. Verify the shim raises ``AttributeError`` for a guaranteed-
    nonexistent name, and that the error message mentions the legacy
    package so the operator knows where the lookup landed.
    """
    # Arrange
    snippet = """
        import warnings
        warnings.simplefilter("ignore")
        import scitex_cloud
        bogus = "definitely_not_a_real_symbol_xyz_42"
        try:
            getattr(scitex_cloud, bogus)
        except AttributeError as exc:
            assert "scitex_cloud" in str(exc), f"missing module name: {exc!r}"
            print("OK")
        else:
            raise AssertionError(
                "getattr returned silently for an unknown attribute"
            )
    """
    # Act
    ok = _run_snippet_ok(snippet)
    # Assert
    assert ok
