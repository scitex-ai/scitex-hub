# Guest Project & Navigation Flow

**Created**: 2025-10-16
**Purpose**: Allow visitor users to try SciTeX features without signup

## Navigation Logic

### Header Module Links Routing

The header Scholar/Code/Viz/Writer buttons route users based on their authentication status:

```
┌─────────────────┬──────────────────────┬────────────────────────────────┐
│ User Status     │ Context              │ Link Destination               │
├─────────────────┼──────────────────────┼────────────────────────────────┤
│ In Project      │ /<user>/<project>/*  │ /<user>/<project>/writer/      │
│ Logged In       │ Not in project       │ /writer/ (landing page)        │
│ Visitor       │ Anywhere             │ /guest/demo-project/writer/    │
└─────────────────┴──────────────────────┴────────────────────────────────┘
```

### Implementation

**Context Processor** (`apps/workspace_app/context_processors.py`):
```python
def project_context(request):
    """
    Provides:
    - 'project': Current project if URL matches /<username>/<project>/
    - 'guest_project_url': Always provides '/guest/demo-project'
    """
```

**Header Template** (`templates/partials/global_header.html`):
```html
{% if project %}
  <!-- In project context: stay in project -->
  <a href="/{{ project.owner.username }}/{{ project.slug }}/writer/">Writer</a>

{% elif user.is_authenticated %}
  <!-- Logged in, not in project: go to landing -->
  <a href="/writer/">Writer</a>

{% else %}
  <!-- Visitor: go to guest project -->
  <a href="{{ guest_project_url }}/writer/">Writer</a>
{% endif %}
```

## Guest Project Details

**URL**: `/guest/demo-project/`

**Workspace URLs**:
- `/guest/demo-project/writer/` → Demo manuscript editor
- `/guest/demo-project/scholar/` → Demo bibliography search
- `/guest/demo-project/console/` → Demo console workspace
- `/guest/demo-project/viz/` → Demo visualization workspace

**Features**:
- ✅ Try all module features
- ✅ Pre-populated with example content
- ⚠️ Read-only for visitor users
- ⚠️ Changes not persisted (session-only)
- 💡 Prompt to sign up to save work

## User Flow Examples

### Example 1: Visitor User Exploring
```
1. Visit https://scitex.cloud/
2. Click "Writer" in header
   → Routed to /guest/demo-project/writer/
3. Try editing demo manuscript
4. Click "Save" → Prompt: "Sign up to save your work"
5. After signup → Data migrated to user's own project
```

### Example 2: Logged-in User Without Project
```
1. User logged in, no projects yet
2. Click "Writer" in header
   → Routed to /writer/ (landing page)
3. Landing page shows:
   - "Create your first project to start writing"
   - [Create Project] button
4. After creating project → Auto-redirect to /<username>/<project>/writer/
```

### Example 3: Working in a Project
```
1. User at /ywatanabe1989/neurovista/writer/
2. Click "Scholar" in header
   → Routed to /ywatanabe1989/neurovista/scholar/
3. Click "Code"
   → Routed to /ywatanabe1989/neurovista/console/
4. Navigation stays within project context
```

## Session Persistence for Guests

For visitor users working in guest project:

```python
# Save work to session
request.session['guest_work'] = {
    'writer': {
        'abstract': '...',
        'introduction': '...',
    },
    'scholar': {
        'saved_papers': [...],
    }
}

# On signup, migrate session data to user project
def migrate_guest_work_to_project(request, new_user, new_project):
    guest_work = request.session.get('guest_work', {})

    # Migrate writer content
    if 'writer' in guest_work:
        manuscript = Manuscript.objects.create(
            owner=new_user,
            project=new_project,
            # ... populate from session
        )

    # Clear session
    del request.session['guest_work']
```

## Implementation Checklist

- ✅ Guest user created (username: `guest`)
- ✅ Demo project created (`/guest/demo-project/`)
- ✅ Context processor provides `guest_project_url`
- ✅ Header routes guests to demo project
- 🔨 TODO: Add "Sign up to save" prompts in modules
- 🔨 TODO: Implement session → project migration on signup
- 🔨 TODO: Populate demo project with example content
- 🔨 TODO: Make guest project read-only with session edits

## Benefits

✅ **Lower barrier to entry**: Try before signup
✅ **Consistent experience**: Same interface for all users
✅ **Clear upgrade path**: "Sign up to save your work"
✅ **No dead-end navigation**: Every link goes somewhere useful

## Technical Notes

### Guest User
- Username: `guest`
- Email: `guest@scitex.ai`
- Password: Unusable (cannot login)
- Purpose: Own the demo project

### Demo Project
- Owner: `guest`
- Slug: `demo-project`
- Status: `active`
- Public: Yes (viewable by all)

### Permissions
```python
# Visitor users have read-only access to guest project
# Edits are stored in session only
# On signup, session data migrates to user's own project
```

---

**Last Updated**: 2025-10-16
**Status**: Implemented
