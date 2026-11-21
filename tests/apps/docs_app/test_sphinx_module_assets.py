"""Sphinx's local Mermaid loader is a JavaScript module, not a download."""
from unittest.mock import patch

from django.test import RequestFactory

from apps.workspace.docs_app._sphinx import sphinx_raw


def test_module_asset_is_served_as_javascript(tmp_path):
    (tmp_path / "mermaid-loader.mjs").write_text('export default "diagram";')
    with patch("apps.workspace.docs_app._sphinx.resolve_sphinx_path", return_value=tmp_path):
        response = sphinx_raw(RequestFactory().get("/"), "scitex-live-paper", "mermaid-loader.mjs")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/javascript")
    assert response.content == b'export default "diagram";'
