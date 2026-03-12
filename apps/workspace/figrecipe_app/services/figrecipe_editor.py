"""FigureEditor wrapper for Django integration.

Imports figrecipe's pure Python functions and serves them via Django
without running Flask. Editor instances cached in-process (stateful)
because Flask route handlers mutate figure state directly.
"""

import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# In-process cache: session_key → (FigureEditor, last_access_time)
_editor_cache: Dict[str, Tuple[Any, float]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


def get_or_create_editor(
    session_key: str,
    recipe_path: str,
    style: Optional[str] = None,
) -> Any:
    """Get cached editor or create a new one.

    Editors are cached in-process because route handlers mutate
    the matplotlib figure directly (labels, legend, axes positions).
    """
    _cleanup_expired()

    if session_key in _editor_cache:
        editor, _ = _editor_cache[session_key]
        _editor_cache[session_key] = (editor, time.time())
        return editor

    editor = _create_editor(recipe_path, style)
    _editor_cache[session_key] = (editor, time.time())
    return editor


def remove_editor(session_key: str) -> None:
    """Remove an editor from cache."""
    _editor_cache.pop(session_key, None)


def _create_editor(
    recipe_path: str,
    style: Optional[str] = None,
) -> Any:
    """Create a FigureEditor from recipe path without running Flask."""
    from figrecipe._editor import _resolve_source, _resolve_style
    from figrecipe._editor._flask_app import FigureEditor
    from figrecipe._editor._hitmap import generate_hitmap, hitmap_to_base64

    fig, resolved_path = _resolve_source(recipe_path)
    style_dict = _resolve_style(style)

    mpl_fig = fig.fig if hasattr(fig, "fig") else fig
    static_png_path = Path(tempfile.mktemp(suffix="_figrecipe_static.png"))
    mpl_fig.savefig(static_png_path, format="png", dpi=150)

    hitmap_img, color_map = generate_hitmap(fig)
    hitmap_b64 = hitmap_to_base64(hitmap_img)

    editor = FigureEditor(
        fig=fig,
        recipe_path=resolved_path,
        style=style_dict,
        port=0,
        host="127.0.0.1",
        static_png_path=static_png_path,
        hitmap_base64=hitmap_b64,
        color_map=color_map,
        hot_reload=False,
        working_dir=Path(recipe_path).parent if recipe_path else Path.cwd(),
    )
    editor._hitmap_generated = True
    logger.info("[Vis] Created FigureEditor for %s", recipe_path)
    return editor


def get_editor_html(editor: Any, base_url: str, dark_mode: bool = False) -> str:
    """Build figrecipe's complete HTML page with Django URL prefixing."""
    from figrecipe._editor import _check_figure_has_content
    from figrecipe._editor._helpers import render_with_overrides
    from figrecipe._editor._templates import build_html_template

    editor.dark_mode = dark_mode

    base64_img, bboxes, img_size = render_with_overrides(
        editor.fig,
        editor.get_effective_style(),
        editor.dark_mode,
    )

    html = build_html_template(
        image_base64=base64_img,
        bboxes=bboxes,
        color_map=editor._color_map,
        style=editor.style,
        overrides=editor.get_effective_style(),
        img_size=img_size,
        style_name=getattr(editor, "_style_name", "SCITEX"),
        hot_reload=False,
        dark_mode=dark_mode,
        figure_has_content=_check_figure_has_content(editor.fig),
        debug_mode=False,
    )

    return _inject_base_url(html, base_url)


def _inject_base_url(html: str, base_url: str) -> str:
    """Override window.fetch to prefix figrecipe URLs with Django path."""
    fetch_override = f"""<script>
(function() {{
  var _origFetch = window.fetch;
  var BASE = '{base_url}';
  window.fetch = function(url) {{
    var args = Array.prototype.slice.call(arguments);
    if (typeof url === 'string' && url.startsWith('/') && !url.startsWith(BASE)) {{
      args[0] = BASE + url;
    }}
    return _origFetch.apply(this, args);
  }};
}})();
</script>"""
    return html.replace("<script>", fetch_override + "\n<script>", 1)


def make_session_key(user_id: int, recipe_path: str) -> str:
    """Build cache key from user ID and recipe path."""
    return f"figrecipe_{user_id}_{recipe_path}"


def _cleanup_expired() -> None:
    """Remove expired editors from cache."""
    now = time.time()
    expired = [
        k for k, (_, ts) in _editor_cache.items() if now - ts > _CACHE_TTL_SECONDS
    ]
    for k in expired:
        _editor_cache.pop(k, None)
