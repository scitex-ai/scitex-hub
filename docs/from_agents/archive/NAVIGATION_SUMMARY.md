# SciTeX Cloud Navigation Summary

**Updated**: 2025-10-16

## URL Structure

### Visitor Users (Guests)
```
Click any module link → /guest-<16-random-chars>/default/<module>/

Examples:
/guest-a9Kf3xL8pQ2mN7vR/default/writer/
/guest-a9Kf3xL8pQ2mN7vR/default/scholar/
/guest-a9Kf3xL8pQ2mN7vR/default/code/
/guest-a9Kf3xL8pQ2mN7vR/default/viz/
```

### Logged-in Users (In Project Context)
```
Within project → /<username>/<project>/<module>/

Examples:
/ywatanabe1989/neurovista-analysis/writer/
/ywatanabe1989/neurovista-analysis/scholar/
/ywatanabe1989/neurovista-analysis/code/
/ywatanabe1989/neurovista-analysis/viz/
```

### Logged-in Users (No Project Context)
```
Click module link → /<module>/ (landing page)

Examples:
/writer/  → Writer marketing page
/scholar/ → Scholar marketing page
/code/    → Code marketing page
/viz/     → Viz marketing page
```

## Implementation

**Files Created/Modified**:
1. `apps/workspace_app/middleware.py` - Guest session ID generation
2. `apps/workspace_app/context_processors.py` - Project context detection
3. `templates/partials/global_header.html` - Context-aware navigation
4. `apps/project_app/views.py` - Module integration views
5. `config/settings/settings_shared.py` - Middleware registration

**Security**:
- 16-character cryptographically random IDs
- URL-safe characters [a-zA-Z0-9_-]
- 62^16 ≈ 4.7 × 10^28 combinations
- Session-isolated workspaces

## Next Steps

1. **Handle guest project access** in module views (allow read-only access)
2. **Session data persistence** (store guest edits in session)
3. **Signup flow** with session migration
4. **Writer app integration** complete (Phase 1-3 from TODO.md)

---

Ready to proceed with writer_app implementation!
