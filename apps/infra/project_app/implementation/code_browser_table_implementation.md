# Code Browser Table Implementation - GitHub Style

## Overview
Improved the file/directory listing table to match GitHub's design with commit information, tooltips, and enhanced interactivity.

## Implementation Date
2025-10-24

## Changes Made

### 1. Backend Changes (`views.py`)

#### Updated `get_git_info()` function
- **Location**: Lines 222-253 (project_detail view) and 1744-1774 (project_directory view)
- **Changes**:
  - Modified git log format to include commit hash: `--format=%an|%ar|%s|%h`
  - Updated return dictionary to include `hash` field
  - Added hash to files and directories context data

**Before:**
```python
result = subprocess.run(
    ['git', 'log', '-1', '--format=%an|%ar|%s', '--', str(path.name)],
    # ...
)
return {
    'author': author,
    'time_ago': time_ago,
    'message': message[:80]
}
```

**After:**
```python
result = subprocess.run(
    ['git', 'log', '-1', '--format=%an|%ar|%s|%h', '--', str(path.name)],
    # ...
)
return {
    'author': author,
    'time_ago': time_ago,
    'message': message[:80],
    'hash': commit_hash
}
```

### 2. Template Changes

#### Updated Templates:
1. `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_directory.html`
2. `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_detail.html`

#### CSS Improvements

**GitHub-style compact design:**
```css
/* Updated padding from 0.5rem 1rem to 8px 16px for tighter spacing */
.file-browser th {
    padding: 8px 16px;
    font-size: 12px;
    color: var(--color-fg-muted);
}

.file-browser td {
    padding: 8px 16px;
    font-size: 14px;
}

/* Added cursor and transition for hover effect */
.file-browser tbody tr {
    cursor: pointer;
    transition: background-color 0.1s ease;
}

/* Improved commit message styling */
.file-browser .commit-message {
    font-size: 12px;
    max-width: 500px;
    cursor: help;
}

.file-browser .commit-time {
    font-size: 12px;
    white-space: nowrap;
}
```

**Tooltip for commit hash:**
```css
.commit-tooltip {
    position: relative;
}

.commit-tooltip:hover::after {
    content: attr(data-hash);
    position: absolute;
    bottom: 100%;
    left: 0;
    background: var(--color-canvas-overlay);
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    z-index: 1000;
    border: 1px solid var(--color-border-default);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}
```

#### HTML Table Structure

**Key improvements:**
1. Made entire rows clickable with `data-href` attribute
2. Added `commit-tooltip` class with `data-hash` attribute for hover tooltips
3. Simplified commit message display (removed author inline, focused on message)
4. Updated column headers to match GitHub style

**Before:**
```html
<tr>
    <td>
        <a href="..." class="file-name">📁 {{ item.name }}</a>
    </td>
    <td class="text-muted commit-message">
        <span title="{{ item.message }}">{{ item.message }}</span>
        {% if item.author %}<span class="commit-author"> by {{ item.author }}</span>{% endif %}
    </td>
    <td class="text-muted text-monospace">
        {% if item.time_ago %}{{ item.time_ago }}{% endif %}
    </td>
</tr>
```

**After:**
```html
<tr data-href="..." class="clickable-row">
    <td>
        <a href="..." class="file-name" onclick="event.stopPropagation();">
            📁 {{ item.name }}
        </a>
    </td>
    <td class="commit-message{% if item.hash %} commit-tooltip{% endif %}"
        {% if item.hash %} data-hash="{{ item.hash }}"{% endif %}>
        {% if item.message %}
            {{ item.message }}
        {% else %}
            <span style="color: var(--color-fg-muted);">No commit message</span>
        {% endif %}
    </td>
    <td class="commit-time">
        {% if item.time_ago %}{{ item.time_ago }}{% endif %}
    </td>
</tr>
```

#### JavaScript Enhancements

**Clickable rows:**
```javascript
// Make table rows clickable
const clickableRows = document.querySelectorAll('.clickable-row');
clickableRows.forEach(row => {
    row.addEventListener('click', function(e) {
        // Don't navigate if clicking on a link directly
        if (e.target.tagName === 'A' || e.target.closest('a')) {
            return;
        }
        const href = this.getAttribute('data-href');
        if (href) {
            window.location.href = href;
        }
    });
});
```

## Features Implemented

### ✅ Column Structure (GitHub-style)
- **Name column** (40% width): File/directory name with icon
- **Commit message column** (45% width): Last commit message with tooltip
- **Commit date column** (15% width): Relative time (e.g., "2 hours ago")

### ✅ Commit Hash Tooltip
- Hover over commit message to see commit hash
- Tooltip appears above the commit message
- Styled with theme-aware colors
- Uses `data-hash` attribute for accessibility

### ✅ Clickable Rows
- Entire row is clickable (not just filename link)
- Click anywhere on row to navigate
- Direct link clicks still work (with `event.stopPropagation()`)
- Cursor changes to pointer on hover

### ✅ Hover Effects
- Subtle background color change on hover
- Smooth 0.1s transition
- Theme-aware using CSS variables
- Matches GitHub's interaction patterns

### ✅ Compact Spacing
- Reduced padding: 8px vertical, 16px horizontal
- Smaller font sizes (12px for metadata, 14px for names)
- Tighter line height for compact display
- More items visible per screen

## Visual Design

### Typography
- **Column headers**: 12px, semi-bold, muted color
- **File names**: 14px, bold (600), brand accent color
- **Commit messages**: 12px, muted color, truncated with ellipsis
- **Commit times**: 12px, muted color, monospace-like appearance

### Colors (Theme-aware)
- Uses CSS custom properties from SciTeX design system
- `var(--color-canvas-subtle)` for hover background
- `var(--color-fg-muted)` for secondary text
- `var(--color-accent-fg)` for links
- `var(--color-border-default)` for borders

### Spacing
- **Header padding**: 8px vertical, 16px horizontal
- **Cell padding**: 8px vertical, 16px horizontal
- **Column widths**: 40% / 45% / 15% for optimal balance
- **Max commit message width**: 500px with text truncation

## Benefits

1. **Better User Experience**: Entire row clickable, easier navigation
2. **More Information**: Commit hash visible on hover without cluttering UI
3. **Faster Scanning**: Compact design shows more items at once
4. **Consistent Design**: Matches GitHub's familiar patterns
5. **Accessibility**: Proper tooltips and cursor feedback
6. **Responsive**: Hover states and transitions feel smooth

## Testing Recommendations

1. Test with various commit message lengths
2. Verify tooltip positioning on different screen sizes
3. Check hover effects in both light and dark themes
4. Test row clicking vs. direct link clicking behavior
5. Verify git info retrieval for files/directories without commits
6. Test with empty directories or files with no git history

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- CSS custom properties required
- JavaScript event listeners (ES6+)
- CSS `::after` pseudo-element for tooltips

## Future Enhancements

Potential improvements for future iterations:
- Add commit hash link to commit detail page
- Show commit author avatar/icon
- Add batch operations (select multiple files)
- Implement sorting by name, date, or commit
- Add file type icons (replace emojis with SVG)
- Show file size in human-readable format
- Add quick preview on hover for text files

## Files Modified

1. `/home/ywatanabe/proj/scitex-cloud/apps/project_app/views.py`
   - Lines 222-282 (project_detail view)
   - Lines 1744-1805 (project_directory view)

2. `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_directory.html`
   - CSS: Lines 51-143
   - HTML: Lines 422-460
   - JavaScript: Lines 555-573

3. `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/project_detail.html`
   - CSS: Lines 36-131
   - HTML: Lines 735-774
   - JavaScript: Lines 981-994

## Related Issues/TODOs

This implementation addresses requirements from `/home/ywatanabe/proj/scitex-cloud/apps/project_app/TODO.md`:
- ✅ Columns: Name · Commit message · Last commit time · Commit hash tooltip
- ✅ Clickable rows with responsive color on hover
- ✅ Compact spacing to match GitHub
- ✅ Commit hash in tooltip on hover over commit message

## Notes

- Git info retrieval may fail for files without git history (handled gracefully)
- Subprocess timeout set to 5 seconds to prevent hanging
- Commit messages truncated to 80 characters in backend for performance
- Frontend truncation to 500px width for visual consistency
