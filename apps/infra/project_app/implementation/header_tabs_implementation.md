# GitHub-Style Header Tabs Implementation

## Overview
This document describes the implementation of GitHub-style repository tabs in the project_app. The tabs provide quick navigation to different sections of a repository, matching GitHub's UI/UX patterns.

## Implementation Date
2025-10-24

## Modified Files

### 1. `/apps/project_app/templates/project_app/project_detail.html`
- **Location**: Line ~617-641 (Tab Navigation section)
- **Changes**: Replaced simple 2-tab navigation with full 8-tab GitHub-style navigation
- **Backup**: `project_detail.html.backup`

### 2. `/apps/project_app/templates/project_app/project_directory.html`
- **Location**: Line ~362-393 (Tab Navigation section)
- **Changes**: Replaced mixed navigation tabs with GitHub-style repository tabs
- **Backup**: `project_directory.html.backup`

### 3. `/apps/project_app/implementation/github_repo_tabs_snippet.html`
- **Purpose**: Reusable HTML snippet for the tab navigation
- **Status**: New file created for reference

## Tab Structure

The implementation adds the following tabs (in order):

| Tab | Icon | URL Pattern | Purpose |
|-----|------|-------------|---------|
| Code | Book/Code icon | `/{username}/{slug}/` | Main repository code view (active by default) |
| Issues | Circle icon | `/{username}/{slug}/issues/` | Track issues and bugs |
| Pull requests | Git branch icon | `/{username}/{slug}/pulls/` | Review code changes |
| Actions | Clock icon | `/{username}/{slug}/actions/` | Automate workflows |
| Projects | Chart icon | `/{username}/{slug}/projects/` | Plan and track work |
| Security | Shield icon | `/{username}/{slug}/security/` | Security policies and analysis |
| Insights | Graph icon | `/{username}/{slug}/insights/` | Repository insights and analytics |
| Settings | Gear icon | `/{username}/{slug}/settings/` | Repository settings |

## Technical Details

### HTML Structure
```html
<div class="repo-tabs" style="display: flex; justify-content: space-between; align-items: center;">
    <div class="scitex-tabs">
        <!-- 8 tab links with SVG icons -->
    </div>
    <div class="btn-group">
        <!-- Copy/Download buttons -->
    </div>
</div>
```

### Icon Implementation
- **Format**: Inline SVG elements (16x16px)
- **Source**: GitHub Octicons
- **Color**: Inherits from parent (currentColor)
- **Alignment**: `vertical-align: text-bottom`

### Styling Classes
- **Container**: `.repo-tabs` - Flexbox container with space-between
- **Tabs wrapper**: `.scitex-tabs` - Contains all tab links
- **Individual tab**: `.scitex-tab` - Single tab link
- **Active state**: `.scitex-tab-active` - Currently active tab

### CSS (from design system)
The tabs use the standardized `.scitex-tabs` component from `/apps/dev_app/static/dev_app/styles/design.css`:

```css
.scitex-tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--color-border-default);
}

.scitex-tab {
    padding: 0.5rem 1rem;
    color: var(--text-secondary);
    border-bottom: 2px solid transparent;
    transition: all 0.2s ease;
}

.scitex-tab:hover {
    color: var(--text-primary);
    border-bottom-color: var(--color-border-default);
}

.scitex-tab-active {
    color: var(--text-primary);
    border-bottom: 2px solid var(--scitex-color-03);
    font-weight: 600;
}
```

## Layout Position

The tab navigation appears in this hierarchy:

```
Global Header (Explore / Scholar / Code / Viz / Writer)
├─ Container
   ├─ Repository Header
   │  ├─ username / repository-name
   │  └─ description
   ├─ Repository Tabs ← THIS IMPLEMENTATION
   │  ├─ Code / Issues / Pull requests / Actions / Projects / Security / Insights / Settings
   │  └─ Copy/Download buttons
   └─ Main Content
      ├─ Sidebar (left)
      └─ Repository content (right)
```

## Key Differences from GitHub

### What Matches GitHub:
1. Tab count and order
2. Icon usage for each tab
3. Horizontal layout below repository name
4. Active state styling
5. Tooltip hints for each tab

### What's Different:
1. **Additional buttons**: Copy/Download concatenated text buttons on the right
2. **Not yet implemented**: Placeholder URLs (issues/, pulls/, etc. may not have backend routes)
3. **Icon style**: SVG inline vs. GitHub's icon font
4. **Color scheme**: Uses SciTeX brand colors instead of GitHub colors

## Responsive Behavior

The existing CSS includes mobile responsiveness:
- Tabs remain horizontal but may wrap on small screens
- Copy/Download button group maintained
- Inherits responsive behavior from `.scitex-tabs` design system component

## Future Improvements

1. **Backend Routes**: Implement actual routes for:
   - `/issues/` - Issue tracking system
   - `/pulls/` - Pull request system
   - `/actions/` - CI/CD workflow system
   - `/projects/` - Project management board
   - `/security/` - Security scanning and policies
   - `/insights/` - Analytics and repository insights

2. **Active State Logic**: Add Django template logic to highlight the correct active tab based on current page

3. **Counter Badges**: Add issue/PR count badges (e.g., "Issues (12)")

4. **Accessibility**: Add ARIA labels and keyboard navigation support

5. **Mobile Menu**: Consider collapsing tabs into a dropdown menu on very small screens

## Testing

To test the implementation:

1. Navigate to any project detail page: `/{username}/{project-slug}/`
2. Verify all 8 tabs are visible
3. Verify "Code" tab shows as active (underlined)
4. Hover over each tab to check hover states
5. Check tooltip hints appear on hover
6. Test on mobile/tablet viewports
7. Verify theme switching (light/dark mode) works correctly

## Notes

- The global header (Explore / Scholar / Code / Viz / Writer) remains unchanged
- Per-repository tabs are now consistent across both `project_detail.html` and `project_directory.html`
- Backup files created before modification for easy rollback
- Changes are purely cosmetic/UX - no backend modifications required yet

## Related Files

- Design system: `/apps/dev_app/static/dev_app/styles/design.css`
- Base template: `/templates/base.html`
- Global header: `/templates/partials/global_header.html`

## Rollback Instructions

If needed, restore original templates:

```bash
mv apps/project_app/templates/project_app/project_detail.html.backup \
   apps/project_app/templates/project_app/project_detail.html

mv apps/project_app/templates/project_app/project_directory.html.backup \
   apps/project_app/templates/project_app/project_directory.html
```

---

**Implementation completed**: 2025-10-24
**Implemented by**: Claude Code Agent
