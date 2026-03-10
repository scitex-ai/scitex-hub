# Sidebar Enhancements - GitHub-like Design

## Summary

Enhanced the sidebar to be more GitHub-like with improved UX, smooth animations, and better hover effects.

## Changes Made

### 1. CSS Enhancements (`sidebar.css`)

#### Container & Toggle Button
- **Smooth animations**: Added cubic-bezier easing for professional feel
- **Background**: Added subtle background color to match GitHub's "About" panel
- **Border**: Right border for better visual separation
- **Toggle button improvements**:
  - Better hover effects with color changes
  - Smooth transform on hover (lift effect)
  - Active state feedback
  - Icon rotates 180° when collapsed
  - Tooltip updates dynamically

#### Hover Effects
All interactive elements now have enhanced hover states:
- **Background color change** to accent-subtle
- **Smooth translateX** animation (slides right on hover)
- **Inset left border** (3px) in accent color for GitHub-like effect
- **Icon color changes** to accent color on hover
- **Box shadow** for depth

#### File Tree
- **Folder icons**: Blue color (#0969da) to match GitHub
- **File items**: Subtle gray color that darkens on hover
- **Chevron animation**: Rotates 90° when folder expanded
- **Active state**: Bold background for selected files

#### Dark Theme Support
- All hover effects and colors adapted for dark theme
- Uses semantic CSS variables for consistency
- Properly styled toggle button for dark mode

### 2. HTML Updates (`_sidebar.html`)

- Added `id="repo-sidebar"` for JavaScript access
- Added `onclick="toggleSidebar()"` to toggle button
- Added dynamic `title` attribute for tooltip
- Improved project name styling (font-weight: 600, font-size: 16px)
- Better spacing with margin-top on file tree

### 3. JavaScript Enhancements (`_project_scripts.html`)

#### localStorage Support
- **Remembers state**: Saves 'collapsed' or 'expanded' state
- **Default behavior**: Starts collapsed, but respects localStorage
- **Key**: `scitex-sidebar-state`

#### Toggle Function Improvements
- Updates tooltip text dynamically
- Handles missing `repo-layout` gracefully
- Smooth class transitions
- Console logging for debugging

#### Initialization
- Checks localStorage on page load
- Applies saved state or defaults to collapsed
- Updates toggle button tooltip correctly

## Features

### 1. Collapsible by Default
- Sidebar starts collapsed (60px width)
- Only toggle button visible when collapsed
- Clean, minimal look matching GitHub's approach

### 2. Larger When Expanded
- Expands to 420px (was 380px)
- More readable fonts (14-16px)
- Larger icons (18px)
- Better spacing throughout

### 3. Smooth Animations
- 0.3s cubic-bezier transitions
- Content fades in/out smoothly
- No jarring state changes

### 4. Enhanced Hover Effects
- Background color changes
- Slide-right animation (3-4px)
- Left border accent
- Icon color changes
- Smooth transitions (0.2s)

### 5. localStorage Persistence
- Remembers user preference
- Works across page navigation
- Can be reset by clearing localStorage

## Testing

### Test URL
```
http://127.0.0.1:8000/ywatanabe/test7/.git/
```

### Test Scenarios

1. **Initial Load (Collapsed)**
   - Sidebar should be 60px wide
   - Only toggle button visible
   - Content hidden

2. **Toggle to Expand**
   - Click toggle button
   - Sidebar expands to 420px
   - File tree becomes visible
   - Smooth animation

3. **Hover Effects**
   - Hover over file tree items
   - Should see background change
   - Slide animation
   - Icon color change

4. **Refresh Page**
   - Should remember last state
   - If expanded before, stays expanded
   - If collapsed before, stays collapsed

5. **Dark Mode**
   - Toggle dark mode (moon icon)
   - All colors should adapt
   - Hover effects still work

## Files Modified

1. `/home/ywatanabe/proj/scitex-cloud/apps/project_app/static/project_app/css/components/sidebar.css`
   - Enhanced with GitHub-like styling
   - Better hover effects
   - Dark theme support

2. `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/partials/_sidebar.html`
   - Added proper IDs
   - Improved onclick handler
   - Better styling

3. `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/partials/_project_scripts.html`
   - Enhanced toggle function
   - localStorage support
   - Dynamic tooltip updates

## Screenshots

### Collapsed State (Initial)
- Width: 60px
- Only toggle button visible
- Minimal space usage

### Expanded State (After Toggle)
- Width: 420px
- Full file tree visible
- Larger fonts and icons
- Better readability

### Hover Effects
- Background: accent-subtle (#ddf4ff in light mode)
- Left border: 3px accent-emphasis (#0969da)
- Icon color changes to accent
- Smooth slide animation

## Design Philosophy

Following GitHub's approach:
1. **Collapsed by default** - More screen space for content
2. **Easy to expand** - One click on obvious button
3. **Smooth animations** - Professional feel
4. **Persistent state** - Remembers user preference
5. **Accessible** - Proper ARIA labels and tooltips
6. **Dark mode support** - Consistent theming

## Browser Compatibility

- Modern browsers with CSS Grid support
- localStorage API required
- CSS custom properties (variables) required
- Tested on Chrome/Edge

## Future Enhancements

Potential improvements:
1. Keyboard shortcut (e.g., Ctrl+B) to toggle
2. Resize handle for custom width
3. Pin/unpin favorite files
4. Search within file tree
5. File tree icons based on file type
6. Drag-and-drop file operations
