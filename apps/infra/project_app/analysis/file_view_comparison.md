# File View UI Comparison: GitHub vs SciTeX

**Analysis Date:** 2025-10-24
**GitHub URL:** https://github.com/SciTeX-AI/scitex-cloud/blob/develop/apps/auth_app/urls.py
**SciTeX URL:** http://127.0.0.1:8000/ywatanabe/test7/blob/scitex/writer/scripts/examples/link_project_assets.sh

## Executive Summary

This document compares the file view UI between GitHub and SciTeX to identify specific design and functional differences. The analysis covers header elements, code display area, toolbar buttons, and metadata presentation.

---

## 1. Header / Breadcrumb Navigation

### GitHub
- **Layout:** Horizontal breadcrumb at top of content area
- **Structure:** `scitex-cloud / apps / auth_app / urls.py`
- **Style:**
  - Links separated by forward slashes `/`
  - Each path component is clickable
  - Final filename (`urls.py`) appears as heading (H1)
  - Clean, minimal styling with subtle link colors
- **Additional Elements:**
  - "Copy path" button with icon
  - "More file actions" menu (three dots)

### SciTeX
- **Layout:** Horizontal breadcrumb navigation
- **Structure:** `ywatanabe / test7 / scitex / writer / scripts / examples / link_project_assets.sh`
- **Style:**
  - Links separated by forward slashes `/`
  - Each path component is clickable
  - Final filename displayed as plain text (not a heading)
  - Similar minimal styling
- **Additional Elements:**
  - File size display: "link_project_assets.sh 2.7 KB"
  - Action buttons on right side (Download, Copy, Raw, Edit)

**Key Differences:**
- GitHub shows filename as H1 heading; SciTeX shows it as regular text
- SciTeX displays file size inline with filename
- SciTeX has more prominent action buttons (with emoji icons)
- GitHub has copy path functionality; SciTeX doesn't show this

---

## 2. Branch Selector

### GitHub
- **Location:** Left sidebar, below "Files" heading
- **Style:**
  - Button labeled "develop branch"
  - Branch icon visible
  - Dropdown arrow indicator
  - Part of file tree navigation panel
- **Functionality:** Allows switching between branches

### SciTeX
- **Location:** Not visible in file view
- **Functionality:** Branch switching not available in this view

**Key Differences:**
- GitHub has prominent branch selector in file tree panel
- SciTeX appears to lack branch selection in file view

---

## 3. File Tree / Sidebar

### GitHub
- **Presence:** YES - Left sidebar panel
- **Features:**
  - Collapsible file tree
  - "Collapse file tree" toggle button
  - "Go to file" search box
  - Full directory structure visible
  - Current file highlighted (`urls.py`)
  - Expandable/collapsible folders
  - File/folder icons
- **Width:** Resizable with draggable splitter

### SciTeX
- **Presence:** NO
- **Features:** None - no file tree visible

**Key Differences:**
- GitHub provides full navigable file tree
- SciTeX has minimal navigation (breadcrumb only)
- This is a major functional difference

---

## 4. Code Area

### GitHub

#### Line Numbers
- **Style:**
  - Light gray color
  - Right-aligned in dedicated column
  - Clickable (can select lines)
  - Hover state available
  - Small expand/collapse button appears on line 21

#### Code Display
- **Container:** Clean white/light background (in light mode)
- **Syntax Highlighting:**
  - Keywords in purple/magenta (`from`, `import`, `path`)
  - Strings in blue
  - Comments in gray
  - Function names in standard color
- **Spacing:** Comfortable line height
- **Font:** Monospace, appears to be GitHub's standard code font
- **Border/Shadow:** Subtle border, no prominent shadow
- **Edge Style:** Rounded corners, clean appearance

### SciTeX

#### Line Numbers
- **Style:**
  - Gray/white color on dark background
  - Left-aligned in dedicated column
  - All line numbers visible (1-87)
  - Simple, clean appearance

#### Code Display
- **Container:** Dark background (dark theme active)
- **Syntax Highlighting:**
  - Keywords in orange/red (`if`, `then`, `for`, `do`)
  - Variables in white/light blue
  - Strings in orange
  - Comments in gray
  - Echo statements in cyan/blue
- **Spacing:** Compact line height
- **Font:** Monospace font
- **Border/Shadow:** No visible border or shadow
- **Edge Style:** No rounded corners, flush edges
- **Layout:** Uses table structure (`<table>` with rows)

**Key Differences:**
- **Theme:** GitHub shows light theme; SciTeX shows dark theme
- **Line number alignment:** GitHub right-aligned, SciTeX left-aligned
- **Syntax highlighting:** Different color schemes entirely
- **Code container:** GitHub has subtle borders/rounded corners; SciTeX is flush
- **Line number interactivity:** GitHub has expand/collapse on some lines; SciTeX doesn't
- **Structure:** GitHub uses more sophisticated DOM; SciTeX uses simple table

---

## 5. Toolbar Buttons

### GitHub
- **Location:** Top-right of code area
- **Buttons:**
  1. **Raw** - Text link with subtle styling
  2. **Copy raw file** - Icon button (copy icon)
  3. **Download raw file** - Icon button (download icon)
  4. **Open symbols panel** - Icon button (symbols/outline icon)
- **Style:**
  - Minimal, icon-based
  - Monochrome icons
  - Hover states
  - Grouped together in compact row

### SciTeX
- **Location:** Top-right, above code area
- **Buttons:**
  1. **📥 Download** - Button with emoji and text
  2. **📋 Copy** - Button with emoji and text
  3. **🔗 Raw** - Link with emoji and text
  4. **✏️ Edit** - Link with emoji and text (highlighted in blue)
- **Style:**
  - Emoji icons with text labels
  - More colorful and prominent
  - Edit button has blue/cyan background highlight
  - Larger, more visible buttons

**Key Differences:**
- **Icon style:** GitHub uses SVG icons; SciTeX uses emojis
- **Button prominence:** SciTeX buttons are larger and more visible
- **Edit functionality:** SciTeX prominently shows Edit; GitHub doesn't in this view
- **Symbols panel:** GitHub has symbols/outline feature; SciTeX doesn't
- **Text labels:** SciTeX shows text with emojis; GitHub mostly icon-only

---

## 6. Metadata Display

### GitHub
- **Location:** Below breadcrumb, above code area
- **"Latest commit" Section:**
  - User avatar (ywatanabe1989)
  - Username link
  - Commit message: "feat: Create clean permissions_app with GitLab-style RBAC"
  - Commit hash: `50764fc` (clickable)
  - Timestamp: "Oct 17, 2025" with relative time "last week"
  - "History" button with icon
- **File Metadata Section:**
  - File view tabs: "Code" | "Blame"
  - File attributes: "executable file"
  - File stats: "39 lines (33 loc) · 1.18 KB"
- **Style:**
  - Gray background section
  - Well-organized, horizontal layout
  - Clear visual hierarchy

### SciTeX
- **Location:** Not visible in file view
- **Information:** None displayed
- **Style:** N/A

**Key Differences:**
- **Major difference:** GitHub shows extensive metadata; SciTeX shows none
- GitHub displays commit info, author, history, file stats
- SciTeX only shows filename and file size
- GitHub has "Code" and "Blame" view options
- No git integration visible in SciTeX file view

---

## 7. Visual Design & Styling

### GitHub
- **Theme:** Light theme (white/light gray background)
- **Color Scheme:** Minimal, professional
- **Spacing:** Generous padding and margins
- **Typography:**
  - Clean sans-serif for UI
  - Monospace for code
  - Good hierarchy with different font sizes
- **Borders/Shadows:** Subtle borders, light shadows on containers
- **Overall Feel:** Clean, professional, enterprise-grade

### SciTeX
- **Theme:** Dark theme (dark blue/gray backgrounds)
- **Color Scheme:** Dark mode with blue accents
- **Spacing:** Tighter, more compact
- **Typography:**
  - Sans-serif for UI
  - Monospace for code
  - Consistent sizing
- **Borders/Shadows:** Minimal, mostly borderless
- **Overall Feel:** Modern, dark, streamlined

**Key Differences:**
- **Theme:** Opposite (light vs dark)
- **Density:** GitHub more spacious; SciTeX more compact
- **Visual weight:** GitHub uses more borders/containers; SciTeX is flatter
- **Complexity:** GitHub has more UI elements and sections

---

## 8. Missing Features in SciTeX

Based on GitHub's file view, SciTeX is missing:

1. **File Tree Sidebar** - No navigable directory structure
2. **Branch Selector** - Cannot switch branches in file view
3. **Git Metadata**:
   - No commit information display
   - No author information
   - No commit history link
   - No timestamp
4. **File Statistics**:
   - No lines of code count
   - No file attributes (executable, etc.)
5. **Blame View** - No git blame functionality
6. **Symbols/Outline Panel** - No code structure navigation
7. **Line Selection** - No visible URL hash linking to specific lines
8. **Copy Path Button** - No quick path copying
9. **Search in Repository** - No file search from this view

---

## 9. Unique Features in SciTeX

Features present in SciTeX but not in GitHub's file view:

1. **Edit Button** - Prominent edit functionality in read view
2. **Emoji Icons** - More visual, friendly button icons
3. **Integrated Navigation Header** - Top navigation bar with project selector
4. **Direct Project Switching** - Dropdown to switch between projects
5. **Application Tabs** - Scholar, Code, Viz, Writer tabs in header

---

## 10. Recommendations for SciTeX

To achieve feature parity with GitHub while maintaining SciTeX's unique identity:

### High Priority
1. **Add Git Metadata Display**
   - Show latest commit info (author, message, hash, date)
   - Add "History" link to file history
   - Display file statistics (lines, size, attributes)

2. **Implement File Tree Sidebar**
   - Collapsible directory navigation
   - Current file highlighting
   - Search/filter functionality
   - Resizable panel

3. **Add Branch Selector**
   - Allow viewing file across different branches
   - Show current branch prominently

### Medium Priority
4. **Line Linking & Selection**
   - Make line numbers clickable
   - Support URL hash for specific lines (#L10-L20)
   - Highlight selected lines

5. **Code Navigation**
   - Add symbols/outline panel for large files
   - Support jumping to functions/classes

6. **Blame View**
   - Show git blame information per line
   - Link to commits for each change

### Low Priority / Keep SciTeX Unique
7. **Maintain Emoji Icons** - These make SciTeX more approachable
8. **Keep Edit Button Prominent** - This is good for workflow
9. **Dark Theme Default** - Can be SciTeX's preference, but offer theme toggle

### Style Improvements
10. **Add Subtle Borders** - Code area could benefit from light border/shadow
11. **Increase Line Height** - Code readability could improve with more spacing
12. **Consider Rounded Corners** - On code container for polish

---

## 11. Screenshots Reference

- **GitHub File View:** `/home/ywatanabe/proj/scitex-cloud/.playwright-mcp/github_file_view.png`
- **SciTeX File View:** `/home/ywatanabe/proj/scitex-cloud/.playwright-mcp/scitex_file_view_full.png`

---

## Conclusion

GitHub's file view is significantly more feature-rich, particularly in terms of:
- Git integration and metadata
- Navigation capabilities (file tree, search)
- Code exploration tools (symbols, blame)

SciTeX's file view is more streamlined and minimal, with strengths in:
- Direct editing access
- Clean, focused interface
- Dark theme aesthetic

The primary gap is the absence of git-related features and navigation tools in SciTeX. Implementing these while maintaining SciTeX's clean aesthetic would bring it closer to GitHub's functionality while preserving its unique character.
