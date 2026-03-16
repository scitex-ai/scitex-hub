"""FigRecipe app URLs — thin wrapper delegating to figrecipe._django."""

from __future__ import annotations

from .figrecipe import urlpatterns as figrecipe_patterns
from .pages import urlpatterns as page_patterns

app_name = "figrecipe_app"

urlpatterns = page_patterns + figrecipe_patterns


# EOF
