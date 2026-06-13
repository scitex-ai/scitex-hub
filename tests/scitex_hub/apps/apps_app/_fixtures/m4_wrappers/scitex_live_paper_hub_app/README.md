# Live Paper

Interactive paper viewer with M4 re-review chip

## Structure

```
scitex_live_paper_hub_app/
  __init__.py          # App init
  apps.py              # Django AppConfig
  views.py             # View functions and context builder
  urls.py              # URL routing
  tests.py             # Test suite
  skill.py             # LLM skill registration
  manifest.json        # App metadata
  templates/scitex_live_paper_hub_app/    # HTML templates
    index.html         # Full page (extends global_base)
    index_partial.html # AJAX-loadable partial
  static/scitex_live_paper_hub_app/css/   # Scoped stylesheets
  .agents/             # AI agent configuration
  LICENSE              # License file
  README.md            # This file
```

## Development

1. Edit `templates/scitex_live_paper_hub_app/index_partial.html` to build your UI
2. Add view logic in `views.py`
3. Add styles in `static/scitex_live_paper_hub_app/css/scitex_live_paper_hub_app.css`
4. Run tests: `pytest apps/scitex_live_paper_hub_app/tests.py`

## Testing in Workspace

To test your app in the SciTeX workspace, use **Dev Install**:

1. Push your app to a Gitea repository
2. Go to Hub → Explore → click "Dev Install" on your repo
3. Your app appears as a workspace tab immediately

Alternatively, from the CLI:
```bash
scitex-cloud app dev .
```

Note: Dev Install is the standard path for external apps. Do NOT edit
`registry.py` or `INSTALLED_APPS` — those are for platform-builtin modules only.

## Submission

When ready to publish:

1. Run validation: `scitex-cloud app validate .`
2. Submit: use the Apps settings panel in your project

## License

Live Paper is licensed under AGPL-3.0 — see `LICENSE` for details.
