# SciTeX URL Structure

## Summary

**Problem:** With GitHub-style `/<username>/<project>` URLs, we need to reserve certain paths to prevent conflicts.

**Solution:**
1. Icons made smaller (32px containers with 16px icons)
2. Reserved paths list added to `config/urls.py`
3. Username validator created in `apps/auth_app/validators.py`
4. URLs registered in correct order (apps before username pattern)

## Reserved URL Prefixes

Cannot be used as usernames:

**System Apps:**
`admin`, `auth`, `billing`, `cloud`, `code`, `core`, `dev`, `docs`, `integrations`, `project`, `scholar`, `viz`, `writer`

**Resources:**
`static`, `media`, `api`, `new`

**Common Words:**
`about`, `help`, `support`, `contact`, `terms`, `privacy`, `settings`, `dashboard`, `profile`, `account`, `login`, `logout`, `signup`, `register`, `reset`, `verify`, `confirm`

**Special:**
`guest-*` (reserved for guest sessions), `robots`, `sitemap`, `favicon`

## URL Order (config/urls.py)

```python
# 1. Admin
path("admin/", ...)

# 2. Apps (auto-discovered: /auth/, /integrations/, etc.)
discover_app_urls()

# 3. Reserved paths
path("new/", ...)

# 4. Username pattern (MUST BE LAST)
path("<str:username>/", ...)
```

## Integration URLs

All working at `/integrations/`:
- `/integrations/` - Dashboard ✅
- `/integrations/orcid/connect/` - ORCID OAuth
- `/integrations/slack/configure/` - Slack webhooks
- `/integrations/export/<id>/bib/` - BibTeX export

## Status

✅ Icons resized to 32px containers (w-8 h-8) with 16px SVGs (w-4 h-4)
✅ Reserved paths documented in config/urls.py
✅ Username validator created at apps/auth_app/validators.py
✅ Integrations working correctly

The `/integrations/` path is now properly reserved and won't conflict with usernames!
