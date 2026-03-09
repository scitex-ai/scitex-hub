# Branch Selector and Action Buttons Implementation

## Overview
This document describes the implementation of GitHub-style repository meta line with branch selector and action buttons for the SciTeX Cloud project detail page.

## Date
2025-10-24

## Requirements
From TODO.md:
- Add "user / repo" display (already exists)
- Add branch selector dropdown (show current branch, allow switching)
- Add Watch/Star/Fork buttons (similar to GitHub)

## Implementation Plan

### 1. CSS Styles to Add

Add these styles to the `<style>` section in `project_detail.html`:

```css
/* GitHub-style repo action buttons */
.repo-action-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    line-height: 20px;
    white-space: nowrap;
    background: var(--color-canvas-default);
    border: 1px solid var(--color-border-default);
    border-radius: 6px;
    color: var(--color-fg-default);
    cursor: pointer;
    transition: all 0.2s ease;
}

.repo-action-btn:hover {
    background: var(--color-canvas-subtle);
    border-color: var(--color-fg-muted);
}

.repo-action-btn:active {
    background: var(--color-canvas-default);
    transform: scale(0.97);
}

.repo-action-btn.active {
    background: var(--color-accent-emphasis);
    color: #ffffff;
    border-color: var(--color-accent-emphasis);
}

.repo-action-icon {
    fill: currentColor;
    vertical-align: text-bottom;
}

.repo-action-count {
    display: inline-flex;
    min-width: 20px;
    padding: 0 6px;
    font-size: 12px;
    font-weight: 500;
    background: var(--color-canvas-subtle);
    border: 1px solid var(--color-border-default);
    border-radius: 2em;
    margin-left: 2px;
}

/* Branch selector */
.branch-selector {
    position: relative;
    display: inline-block;
}

.branch-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    background: var(--color-canvas-default);
    border: 1px solid var(--color-border-default);
    border-radius: 6px;
    color: var(--color-fg-default);
    cursor: pointer;
}

.branch-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 100;
    margin-top: 4px;
    min-width: 250px;
    max-height: 400px;
    overflow-y: auto;
    background: var(--color-canvas-default);
    border: 1px solid var(--color-border-default);
    border-radius: 6px;
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    display: none;
}

.branch-dropdown.show {
    display: block;
}
```

### 2. HTML Structure to Replace

Replace the repo header section (lines 538-552) with:

```html
<!-- Repository Header -->
<div class="repo-header">
    <div style="display: flex; align-items: center; justify-content: space-between; gap: 1rem;">
        <!-- Left: User / Repo -->
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <a href="/{{ project.owner.username }}/" style="color: var(--color-accent-fg); text-decoration: none; font-weight: 400;">
                {{ project.owner.username }}
            </a>
            <span style="color: var(--color-fg-muted);">/</span>
            <a href="/{{ project.owner.username }}/{{ project.slug }}/" class="repo-title">
                {{ project.name }}
            </a>
        </div>

        <!-- Right: Action Buttons -->
        <div style="display: flex; gap: 0.5rem; align-items: center;">
            <!-- Branch Selector -->
            <div class="branch-selector">
                <button class="branch-btn" onclick="toggleBranchDropdown()">
                    <svg class="branch-icon" width="16" height="16" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M11.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5zm-2.25.75a2.25 2.25 0 1 1 3 2.122V6A2.5 2.5 0 0 1 10 8.5H6a1 1 0 0 0-1 1v1.128a2.251 2.251 0 1 1-1.5 0V5.372a2.25 2.25 0 1 1 1.5 0v1.836A2.492 2.492 0 0 1 6 7h4a1 1 0 0 0 1-1v-.628A2.25 2.25 0 0 1 9.5 3.25zM4.25 12a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5zM3.5 3.25a.75.75 0 1 1 1.5 0 .75.75 0 0 1-1.5 0z"></path>
                    </svg>
                    <span id="current-branch">{{ project.current_branch|default:"main" }}</span>
                    <svg style="width: 12px; height: 12px;" viewBox="0 0 16 16">
                        <path d="m4.427 7.427 3.396 3.396a.25.25 0 0 0 .354 0l3.396-3.396A.25.25 0 0 0 11.396 7H4.604a.25.25 0 0 0-.177.427Z"></path>
                    </svg>
                </button>
                <div class="branch-dropdown" id="branch-dropdown">
                    <div class="branch-dropdown-header">Switch branches/tags</div>
                    <ul class="branch-list" id="branch-list">
                        <li class="branch-list-item active" onclick="switchBranch('{{ project.current_branch|default:"main" }}')">
                            <svg class="branch-icon" width="16" height="16" viewBox="0 0 16 16">
                                <path fill-rule="evenodd" d="M11.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5zm-2.25.75a2.25 2.25 0 1 1 3 2.122V6A2.5 2.5 0 0 1 10 8.5H6a1 1 0 0 0-1 1v1.128a2.251 2.251 0 1 1-1.5 0V5.372a2.25 2.25 0 1 1 1.5 0v1.836A2.492 2.492 0 0 1 6 7h4a1 1 0 0 0 1-1v-.628A2.25 2.25 0 0 1 9.5 3.25zM4.25 12a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5zM3.5 3.25a.75.75 0 1 1 1.5 0 .75.75 0 0 1-1.5 0z"></path>
                            </svg>
                            <span>{{ project.current_branch|default:"main" }}</span>
                        </li>
                    </ul>
                </div>
            </div>

            <!-- Watch Button -->
            <button class="repo-action-btn" id="watch-btn" onclick="handleWatch(event)">
                <svg class="repo-action-icon" viewBox="0 0 16 16" width="16" height="16">
                    <path d="M8 2c1.981 0 3.671.992 4.933 2.078 1.27 1.091 2.187 2.345 2.637 3.023a1.62 1.62 0 0 1 0 1.798c-.45.678-1.367 1.932-2.637 3.023C11.67 13.008 9.981 14 8 14c-1.981 0-3.671-.992-4.933-2.078C1.797 10.83.88 9.576.43 8.898a1.62 1.62 0 0 1 0-1.798c.45-.677 1.367-1.931 2.637-3.022C4.33 2.992 6.019 2 8 2ZM1.679 7.932a.12.12 0 0 0 0 .136c.411.622 1.241 1.75 2.366 2.717C5.176 11.758 6.527 12.5 8 12.5c1.473 0 2.825-.742 3.955-1.715 1.124-.967 1.954-2.096 2.366-2.717a.12.12 0 0 0 0-.136c-.412-.621-1.242-1.75-2.366-2.717C10.824 4.242 9.473 3.5 8 3.5c-1.473 0-2.825.742-3.955 1.715-1.124.967-1.954 2.096-2.366 2.717ZM8 10a2 2 0 1 1-.001-3.999A2 2 0 0 1 8 10Z"></path>
                </svg>
                <span>Watch</span>
                <span class="repo-action-count" id="watch-count">0</span>
            </button>

            <!-- Star Button -->
            <button class="repo-action-btn" id="star-btn" onclick="handleStar(event)">
                <svg class="repo-action-icon" viewBox="0 0 16 16" width="16" height="16">
                    <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"></path>
                </svg>
                <span>Star</span>
                <span class="repo-action-count" id="star-count">0</span>
            </button>

            <!-- Fork Button -->
            <button class="repo-action-btn" id="fork-btn" onclick="handleFork(event)">
                <svg class="repo-action-icon" viewBox="0 0 16 16" width="16" height="16">
                    <path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"></path>
                </svg>
                <span>Fork</span>
                <span class="repo-action-count" id="fork-count">0</span>
            </button>
        </div>
    </div>
    {% if project.description %}
    <div class="repo-description">{{ project.description }}</div>
    {% endif %}
</div>
```

### 3. JavaScript Functions to Add

Add these functions to the `<script>` section:

```javascript
// Branch selector functions
function toggleBranchDropdown() {
    const dropdown = document.getElementById('branch-dropdown');
    dropdown.classList.toggle('show');

    // Load branches if not loaded
    if (!dropdown.dataset.loaded) {
        loadBranches();
        dropdown.dataset.loaded = 'true';
    }

    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', closeBranchDropdown);
    }, 0);
}

function closeBranchDropdown(e) {
    const dropdown = document.getElementById('branch-dropdown');
    const selector = document.querySelector('.branch-selector');

    if (!selector.contains(e.target)) {
        dropdown.classList.remove('show');
        document.removeEventListener('click', closeBranchDropdown);
    }
}

async function loadBranches() {
    try {
        const response = await fetch('/{{ project.owner.username }}/{{ project.slug }}/api/branches/');
        const data = await response.json();

        if (data.success && data.branches) {
            const branchList = document.getElementById('branch-list');
            const currentBranch = '{{ project.current_branch|default:"main" }}';

            branchList.innerHTML = data.branches.map(branch => `
                <li class="branch-list-item ${branch === currentBranch ? 'active' : ''}"
                    onclick="switchBranch('${branch}')">
                    <svg class="branch-icon" width="16" height="16" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M11.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5zm-2.25.75a2.25 2.25 0 1 1 3 2.122V6A2.5 2.5 0 0 1 10 8.5H6a1 1 0 0 0-1 1v1.128a2.251 2.251 0 1 1-1.5 0V5.372a2.25 2.25 0 1 1 1.5 0v1.836A2.492 2.492 0 0 1 6 7h4a1 1 0 0 0 1-1v-.628A2.25 2.25 0 0 1 9.5 3.25zM4.25 12a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5zM3.5 3.25a.75.75 0 1 1 1.5 0 .75.75 0 0 1-1.5 0z"></path>
                    </svg>
                    <span>${branch}</span>
                </li>
            `).join('');
        }
    } catch (error) {
        console.error('Failed to load branches:', error);
    }
}

function switchBranch(branchName) {
    console.log('Switching to branch:', branchName);
    document.getElementById('current-branch').textContent = branchName;
    document.getElementById('branch-dropdown').classList.remove('show');

    // TODO: Implement actual branch switching logic
    // This would typically involve updating the project's current_branch field
    // and reloading the file browser to show files from that branch
}

// Action button handlers
async function handleWatch(event) {
    const btn = event.currentTarget;
    const isWatching = btn.classList.contains('active');

    // Toggle watch status
    btn.classList.toggle('active');

    // Update count (placeholder)
    const count = document.getElementById('watch-count');
    const currentCount = parseInt(count.textContent);
    count.textContent = isWatching ? currentCount - 1 : currentCount + 1;

    // TODO: Send API request to update watch status
    console.log(isWatching ? 'Unwatched' : 'Watched', 'project');
}

async function handleStar(event) {
    const btn = event.currentTarget;
    const isStarred = btn.classList.contains('active');

    // TODO: Implement star functionality via social_app
    // For now, just toggle the visual state
    btn.classList.toggle('active');

    const count = document.getElementById('star-count');
    const currentCount = parseInt(count.textContent);
    count.textContent = isStarred ? currentCount - 1 : currentCount + 1;

    console.log(isStarred ? 'Unstarred' : 'Starred', 'project');
}

async function handleFork(event) {
    // TODO: Implement fork functionality
    if (confirm('Fork this repository? This will create a copy under your account.')) {
        console.log('Forking project...');
        // Redirect to fork creation page or trigger fork API
    }
}
```

### 4. API Endpoint to Create

Add this to `views.py`:

```python
@login_required
@require_http_methods(["GET"])
def api_branches(request, username, slug):
    """API endpoint to list Git branches for a project"""
    import subprocess
    from pathlib import Path

    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check access
    has_access = (
        project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists()
        or project.visibility == "public"
    )

    if not has_access:
        return JsonResponse({"success": False, "error": "Permission denied"})

    # Get project path
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        return JsonResponse(
            {"success": False, "error": "Project directory not found"}
        )

    # Check if it's a git repository
    git_dir = project_path / ".git"
    if not git_dir.exists():
        return JsonResponse(
            {"success": True, "branches": [project.current_branch or "main"]}
        )

    try:
        # Get all branches
        result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            branches = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line:
                    # Remove * from current branch
                    branch = line.lstrip('* ')
                    # Skip remote tracking branches (we only want local)
                    if not branch.startswith('remotes/'):
                        branches.append(branch)

            return JsonResponse({
                "success": True,
                "branches": branches,
                "current": project.current_branch or "main"
            })
        else:
            return JsonResponse({
                "success": True,
                "branches": [project.current_branch or "main"]
            })

    except Exception as e:
        logger.error(f"Error listing branches: {e}")
        return JsonResponse({
            "success": True,
            "branches": [project.current_branch or "main"]
        })
```

### 5. URL Pattern to Add

Add this to `urls.py`:

```python
path('<str:username>/<str:slug>/api/branches/', views.api_branches, name='api_branches'),
```

## Testing Checklist

- [ ] Branch selector displays current branch
- [ ] Branch dropdown shows list of available branches
- [ ] Click outside closes branch dropdown
- [ ] Watch button toggles active state
- [ ] Star button toggles active state
- [ ] Fork button shows confirmation
- [ ] Buttons display correct counts
- [ ] Styles match GitHub design
- [ ] Works in both light and dark themes
- [ ] Responsive on mobile devices

## Implementation Status

### IMPLEMENTED (2025-10-24)

**Backend Implementation:**
- Created social interaction models in `/home/ywatanabe/proj/scitex-cloud/apps/project_app/models.py`:
  - `ProjectWatch` - Track users watching projects for notifications
  - `ProjectStar` - Track users starring projects
  - `ProjectFork` - Track project forks
- Created API views in `/home/ywatanabe/proj/scitex-cloud/apps/project_app/api_views_module/api_views.py`:
  - `api_project_watch` - POST endpoint to toggle watch status
  - `api_project_star` - POST endpoint to toggle star status
  - `api_project_fork` - POST endpoint to create project fork
  - `api_project_stats` - GET endpoint to fetch counts and user status
- Added API routes to `/home/ywatanabe/proj/scitex-cloud/apps/project_app/user_urls.py`:
  - `/<username>/<slug>/api/watch/` - Toggle watch
  - `/<username>/<slug>/api/star/` - Toggle star
  - `/<username>/<slug>/api/fork/` - Create fork
  - `/<username>/<slug>/api/stats/` - Get stats
- Created and ran database migration: `0013_projectfork_projectstar_projectwatch.py`

**Frontend Implementation:**
- Updated `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_detail.html`:
  - Added CSS styles for GitHub-style action buttons
  - Added Watch/Star/Fork buttons to repository header
  - Implemented JavaScript handlers for all three actions
  - Added notification system for user feedback
  - Implemented automatic stats loading on page load
  - Added CSRF token handling for POST requests

**Related Names Used:**
- ProjectWatch: `project.project_watchers` (to avoid conflict with other models)
- ProjectStar: `project.project_stars_set` (to avoid conflict with social_app.RepositoryStar)
- ProjectFork: `project.project_forks_set` and `project.forked_from`

## Future Enhancements

1. **Branch Switching**: Implement actual Git checkout functionality
2. **Watch Integration**: Connect to notification system for emails/alerts
3. **Fork Directory Copying**: Implement actual project directory/file copying
4. **Star Analytics**: Add trending/popular projects based on star counts
5. **Real-time Updates**: Implement WebSocket for live count updates
6. **Branch Creation**: Add "Create new branch" option in dropdown
7. **Tag Support**: Add tags to branch selector dropdown
8. **Fork Sync**: Implement syncing forked projects with original

## Notes

- Watch/Star/Fork functionality is now fully implemented with database backing
- Buttons display real counts from the database
- Fork creates a new Project record but doesn't copy files yet
- Related names were chosen to avoid conflicts with social_app models
- All API endpoints require authentication (@login_required)
- Permission checks ensure only authorized users can access projects
