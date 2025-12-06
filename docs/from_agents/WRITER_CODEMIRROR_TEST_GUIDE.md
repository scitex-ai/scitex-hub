# Writer CodeMirror Testing Guide

## Quick Start Testing

### 1. Access the Writer
```bash
# Start the development server (if not already running)
cd /home/ywatanabe/proj/scitex-cloud
source .venv/bin/activate
python manage.py runserver

# Navigate to:
http://localhost:8000/writer/
```

### 2. Visual Inspection Checklist

#### Initial Load
- [ ] CodeMirror editor loads successfully
- [ ] "LaTeX" label visible at top-left
- [ ] Grey header bar spans full width
- [ ] Border radius is rounded (6px)
- [ ] Shadow is subtle and visible
- [ ] Line numbers appear in left gutter
- [ ] Default theme loads correctly

#### Layout
- [ ] Editor fills available vertical space
- [ ] No scrollbars at container level (only within editor)
- [ ] Padding is consistent (matches design system)
- [ ] Header bar doesn't cover first line
- [ ] Line numbers align properly with code

#### Typography
- [ ] Monospace font is readable
- [ ] Font size is appropriate (14px)
- [ ] Line height provides good readability (1.5)
- [ ] Line numbers are subtle but visible

### 3. Functionality Testing

#### Basic Editing
```latex
% Test 1: Type this LaTeX code
\documentclass{article}
\usepackage{amsmath}

\begin{document}
\section{Test}

Hello, World! This is a test.

\begin{equation}
  E = mc^2
\end{equation}

\end{document}
```

- [ ] Syntax highlighting works (commands are colored)
- [ ] Line numbers update as you type
- [ ] Active line is highlighted
- [ ] Cursor is visible
- [ ] Text selection works and is visible

#### Theme Switching
1. [ ] Locate theme selector dropdown (top-right toolbar)
2. [ ] Switch to "Zenburn" theme
   - [ ] Background darkens
   - [ ] Syntax colors change
   - [ ] Border and header remain consistent
   - [ ] "LaTeX" label still visible
3. [ ] Switch to "Eclipse" theme
   - [ ] Background lightens
   - [ ] Syntax colors change
   - [ ] Border and header remain consistent
4. [ ] Preference is saved (refresh page, theme persists)

#### Scrolling
1. [ ] Add more lines (50+ lines of LaTeX)
2. [ ] Vertical scrollbar appears inside editor
3. [ ] Scrolling is smooth
4. [ ] Line numbers scroll with content
5. [ ] Header bar remains fixed at top

#### Long Lines
```latex
% Type a very long line without line breaks
\section{This is a very long section title that should wrap or scroll horizontally depending on the line wrapping setting and should test the horizontal overflow behavior}
```

- [ ] Long lines wrap or scroll horizontally
- [ ] Horizontal scrollbar appears if needed
- [ ] Text remains readable when wrapped

### 4. Responsive Testing

#### Desktop View (>768px)
- [ ] Editor takes full width
- [ ] Font size is 14px
- [ ] Side padding is 1.5rem
- [ ] All toolbar elements visible

#### Tablet View (768px)
- [ ] Editor remains functional
- [ ] Theme selector may be hidden
- [ ] Font size adjusts to 13px
- [ ] Padding reduces to 1rem

#### Mobile View (<768px)
```bash
# Use browser dev tools
# Toggle device toolbar (F12, then Ctrl+Shift+M)
# Select iPhone or Android device
```

- [ ] Editor is usable on mobile
- [ ] Touch scrolling works
- [ ] Virtual keyboard doesn't break layout
- [ ] "LaTeX" label is smaller (0.65rem)

### 5. Light/Dark Mode Testing

#### Light Mode
```bash
# In browser console:
document.documentElement.setAttribute('data-theme', 'light');
```

- [ ] Editor background is light (#ffffff)
- [ ] Text is dark and readable
- [ ] Border is subtle but visible
- [ ] Shadow is light (0.08 alpha)
- [ ] Header bar is light grey
- [ ] Line numbers are subtle

#### Dark Mode
```bash
# In browser console:
document.documentElement.setAttribute('data-theme', 'dark');
```

- [ ] Editor background is dark (#1a2332)
- [ ] Text is light and readable
- [ ] Border is visible on dark background
- [ ] Shadow is stronger (0.3 alpha)
- [ ] Header bar is dark
- [ ] Line numbers remain visible

#### Theme Persistence
1. [ ] Set to dark mode
2. [ ] Select "Zenburn" theme
3. [ ] Refresh page
4. [ ] Theme should still be Zenburn in dark mode
5. [ ] Switch to light mode
6. [ ] Should use last light theme (e.g., "Eclipse")

### 6. Accessibility Testing

#### Keyboard Navigation
- [ ] Tab key inserts spaces (not focus change)
- [ ] Arrow keys navigate cursor
- [ ] Home/End move to line start/end
- [ ] Ctrl+Home/End move to document start/end
- [ ] Ctrl+Z undoes changes
- [ ] Ctrl+Y redoes changes
- [ ] Ctrl+A selects all text
- [ ] Ctrl+C copies selected text
- [ ] Ctrl+V pastes text

#### Focus States
- [ ] Click in editor → border changes to emphasis color
- [ ] Click outside → border returns to default
- [ ] Focus outline is visible (2px)
- [ ] Focus outline has offset for clarity

#### Screen Reader (Optional)
```bash
# On Windows: Enable Narrator (Win+Ctrl+Enter)
# On Mac: Enable VoiceOver (Cmd+F5)
# On Linux: Enable Orca
```

- [ ] Line numbers are announced
- [ ] Cursor position is announced
- [ ] Content is readable
- [ ] Syntax tokens are distinguishable

### 7. Browser Compatibility Testing

#### Chrome/Chromium
```bash
# Test on latest Chrome
# Check DevTools for console errors
```
- [ ] No console errors
- [ ] Rendering is sharp
- [ ] All features work

#### Firefox
```bash
# Test on latest Firefox
# Check Browser Console for errors
```
- [ ] No console errors
- [ ] Font rendering acceptable
- [ ] All features work

#### Safari (Mac only)
```bash
# Test on Safari if available
```
- [ ] No console errors
- [ ] WebKit rendering works
- [ ] All features work

#### Edge (Windows only)
```bash
# Test on Edge if available
```
- [ ] No console errors
- [ ] Chromium-based, should match Chrome
- [ ] All features work

### 8. Performance Testing

#### Load Time
```bash
# Open DevTools → Network tab
# Refresh page
# Check CSS load times
```
- [ ] codemirror-styling.css loads <50ms
- [ ] code-blocks.css loads <50ms
- [ ] No 404 errors for CSS files

#### Runtime Performance
```bash
# Open DevTools → Performance tab
# Start recording
# Type in editor for 10 seconds
# Stop recording
```
- [ ] Frame rate stays 60fps
- [ ] No janky scrolling
- [ ] No layout thrashing
- [ ] Memory usage stable

#### Memory Leaks
```bash
# Open DevTools → Memory tab
# Take heap snapshot
# Type extensively in editor
# Take another heap snapshot
# Compare snapshots
```
- [ ] No significant memory increase
- [ ] No detached DOM nodes
- [ ] No leaked listeners

### 9. Integration Testing

#### With Sidebar
- [ ] Toggle sidebar on/off
- [ ] Editor resizes properly
- [ ] No layout breaks
- [ ] Scrollbars appear correctly

#### With Compilation Panel
- [ ] Click "Compile PDF"
- [ ] Compilation panel opens
- [ ] Editor remains visible
- [ ] Layout adjusts properly

#### With Split View
- [ ] Switch to "Split" view
- [ ] Editor and preview side-by-side
- [ ] Both panels have proper styling
- [ ] Resize works correctly

### 10. Edge Cases

#### Empty Document
- [ ] Open editor with no content
- [ ] Cursor is visible
- [ ] Line 1 is shown in gutter
- [ ] Placeholder works (if implemented)

#### Very Large Document
```latex
% Generate 1000+ lines of LaTeX
% Use a script or paste repeatedly
```
- [ ] Editor handles large files
- [ ] Scrolling remains smooth
- [ ] Line numbers work correctly
- [ ] No performance degradation

#### Special Characters
```latex
% Test special LaTeX characters
\$ \& \% \# \_ \{ \}
É à ü ñ ø
→ ← ↔ ∀ ∃ ∫
```
- [ ] Special characters render correctly
- [ ] Unicode support works
- [ ] No encoding issues
- [ ] Syntax highlighting handles them

#### Copy/Paste
1. [ ] Copy text from external source
2. [ ] Paste into editor
3. [ ] Formatting is preserved
4. [ ] No weird characters
5. [ ] Undo/redo works after paste

### 11. Regression Testing

#### Existing Features
- [ ] Save functionality still works
- [ ] Compile button still works
- [ ] Theme switching still works
- [ ] Section navigation still works
- [ ] Word count still updates
- [ ] Auto-save still works
- [ ] Undo/redo still works

#### User Preferences
- [ ] Theme preference saves
- [ ] Editor content saves
- [ ] Window size remembered
- [ ] Split view preference saves

### 12. Visual Comparison

#### With Design System Code Blocks
1. Navigate to `/dev/design/` (if available)
2. Find code block examples
3. Compare visually with editor:
   - [ ] Border radius matches
   - [ ] Shadow depth matches
   - [ ] Padding matches
   - [ ] Header bar height matches
   - [ ] Label position matches
   - [ ] Typography matches

### 13. Screenshot Testing

#### Take Reference Screenshots
```bash
# Light Mode - Default Theme
# Light Mode - Eclipse Theme
# Dark Mode - Default Theme
# Dark Mode - Zenburn Theme
# Mobile View
# Tablet View
# Focus State
# Selection State
```

Store in: `/docs/screenshots/writer_codemirror/`

### 14. Automated Testing (Optional)

#### CSS Validation
```bash
# Install validator
npm install -g css-validator

# Validate CSS
css-validator /path/to/codemirror-styling.css
```
- [ ] No CSS errors
- [ ] No unknown properties
- [ ] No invalid values

#### Lighthouse Audit
```bash
# Run Lighthouse in Chrome DevTools
# Focus on Accessibility score
```
- [ ] Accessibility score >90
- [ ] No contrast issues
- [ ] No ARIA issues

### 15. User Acceptance Testing

#### Test Users
- [ ] Ask colleagues to test
- [ ] Get feedback on appearance
- [ ] Check if intuitive to use
- [ ] Verify readability

#### Feedback Areas
- Appearance: Professional? Polished?
- Readability: Easy to read code?
- Colors: Syntax highlighting clear?
- Layout: Intuitive? Cluttered?
- Performance: Fast? Responsive?

## Common Issues and Solutions

### Issue: "LaTeX" label not visible
**Solution**: Check z-index, ensure `::before` pseudo-element has `z-index: 100`

### Issue: Header bar covers first line
**Solution**: Verify `padding-top: 2.5rem` on `.CodeMirror`

### Issue: Scrollbars everywhere
**Solution**: Check `overflow: hidden` on `.CodeMirror`, `overflow: auto` on `.CodeMirror-scroll`

### Issue: Border not visible in dark mode
**Solution**: Verify `--border-muted` variable is defined and used

### Issue: Theme colors not applying
**Solution**: Check CSS load order, ensure codemirror-styling.css loads after CodeMirror theme CSS

### Issue: Layout breaks on resize
**Solution**: Verify `flex: 1` and `height: 100%` on `.CodeMirror`

## Success Criteria

All checkboxes above should be checked (✓) for a successful integration.

Minimum passing score: 90% of tests pass

Critical must-pass tests:
- [ ] "LaTeX" label visible
- [ ] Header bar renders
- [ ] Border and shadow present
- [ ] Syntax highlighting works
- [ ] Editing functionality intact
- [ ] Theme switching works
- [ ] No console errors
- [ ] Responsive on mobile
- [ ] Light/dark mode support
- [ ] No regression in existing features

## Reporting Issues

If you find issues, report them with:
1. Browser and version
2. Screen size / viewport
3. Steps to reproduce
4. Expected vs actual behavior
5. Screenshots if visual issue
6. Console errors if applicable

Create issue at: `/docs/from_agents/CODEMIRROR_ISSUES.md`

## Sign-off

Testing completed by: _____________
Date: _____________
All critical tests passed: [ ] Yes [ ] No
Ready for production: [ ] Yes [ ] No

Notes:
_________________________________________________
_________________________________________________
_________________________________________________
