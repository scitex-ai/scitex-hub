# Terminology: GitHub Alignment

**Decision**: Use GitHub terminology for consistency

## GitHub vs SciTeX

### Current (Mixed)
- ❌ "Project" (generic, unclear)
- ❌ "Workspace" (vague)
- ❌ Mixed terminology

### Proposed (GitHub-aligned)
- ✅ "Repository" (matches GitHub)
- ✅ Clear, familiar to developers and researchers

## Terminology Map

| Concept | SciTeX Term | GitHub Term | **Use** |
|---------|-------------|-------------|---------|
| Research work container | Project | Repository | **Repository** |
| List of repositories | Projects | Repositories | **Repositories** |
| Create new | Create Project | New Repository | **New Repository** |
| Settings | Project Settings | Repository Settings | **Repository Settings** |

## URL Structure

### Before
```
/ywatanabe1989/projects/           → Projects list
/ywatanabe1989/neurovista/         → Project dashboard
```

### After (GitHub-aligned)
```
/ywatanabe1989/?tab=repositories   → Repositories list
/ywatanabe1989/neurovista/         → Repository dashboard
```

## Implementation

### Database
- Keep `Project` model name (internal)
- Update display text to "Repository"

### Templates
- "Projects" → "Repositories"
- "Create Project" → "New Repository"
- "Project Name" → "Repository Name"

### URLs
- Already use `?tab=repositories` ✅
- Path: `/<username>/<repository>/` ✅

## Benefits

✅ **Familiar**: Users know GitHub pattern
✅ **Clear**: "Repository" is more specific than "Project"
✅ **Consistent**: Matches Git/GitHub ecosystem
✅ **Professional**: Industry-standard terminology

## Decision

**Use "Repository"** in all user-facing text while keeping `Project` model internally.

---

**Status**: Approved
**Next**: Update all templates and UI text
