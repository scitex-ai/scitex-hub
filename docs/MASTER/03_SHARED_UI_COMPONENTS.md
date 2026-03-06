<!-- ---
!-- Timestamp: 2026-03-02
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/MASTER/03_SHARED_UI_COMPONENTS.md
!-- --- -->

# Shared UI Components for App Plugins

Reusable UI systems that plugins can use out of the box.
Part of the workspace frame — auto-loaded globally, no extra imports needed.

## Resizer (`HorizontalResizer` / `VerticalResizer`)

Split any two panels with a draggable, collapsible resizer.

### Variants

| Class | Data Attribute | Axis | CSS Class |
|-------|---------------|------|-----------|
| `HorizontalResizer` | `data-h-resizer` | Left/Right (width) | `.h-resizer` |
| `VerticalResizer` | `data-v-resizer` | Top/Bottom (height) | `.v-resizer` |

### Usage (HTML only — auto-initialized)

```html
<!-- Horizontal split: sidebar | content -->
<div class="my-sidebar">...</div>
<div class="h-resizer" data-h-resizer
     data-left=".my-sidebar"
     data-right=".my-content"
     data-most-left
     data-threshold="40"
     data-in-app></div>
<div class="my-content">...</div>

<!-- Vertical split: top | bottom -->
<div class="my-top-panel">...</div>
<div class="v-resizer" data-v-resizer
     data-top=".my-top-panel"
     data-bottom=".my-bottom-panel"
     data-most-bottom
     data-threshold="40"
     data-in-app></div>
<div class="my-bottom-panel">...</div>
```

### Data Attributes

| Attribute | Description |
|-----------|-------------|
| `data-left` / `data-right` | CSS selectors for adjacent panels (horizontal) |
| `data-top` / `data-bottom` | CSS selectors for adjacent panels (vertical) |
| `data-most-left` | Left panel collapses when dragged below threshold |
| `data-most-right` | Right panel collapses when dragged below threshold |
| `data-most-top` / `data-most-bottom` | Same for vertical |
| `data-threshold` | Collapse threshold in pixels (default: 40) |
| `data-in-app` | **Required** for in-app resizers (disables frame-level cascade) |
| `data-storage-key` | Custom localStorage key for persistence |

### Behavior

- **Drag**: Mouse drag resizes both adjacent panels proportionally
- **Collapse**: When a panel shrinks below `threshold`, it collapses to its min size
- **Persist**: Panel sizes saved to localStorage and restored on page load
- **Toggle**: Optional toggle button for one-click collapse/expand
- **Cascade**: Frame-level resizers propagate size changes (domino effect); in-app resizers (`data-in-app`) do not

### CSS

Shared styles in `static/shared/css/components/resizer.css` (auto-loaded via `common.css`).
Uses `--workspace-border-default` for idle color and `--workspace-icon-primary` for hover/active accent.

### Programmatic API

For advanced use cases (e.g., PDF iframe optimization during drag):

```typescript
import { HorizontalResizer, VerticalResizer } from "shared/resizer";

// Programmatic init with hooks
const resizer = new HorizontalResizer(element, {
  left: ".editor-panel",
  right: ".preview-panel",
  mostRight: true,
  thresholdPx: 40,
  inApp: true,
  storageKey: "myapp-editor-split",
  onDragStart: () => { iframe.style.visibility = 'hidden'; },
  onDragEnd: () => { iframe.style.visibility = ''; },
});
```

---

## Selector Nav (`.selector-nav`)

Vertical icon+label navigation strip for mode switching within a module.

### Usage

```html
<nav class="selector-nav" id="myapp-mode-selector" data-indicator="right">
    <button class="selector-nav-item active" onclick="switchMode('chart')">
        <i class="fas fa-chart-bar"></i>
        <span class="selector-nav-label">Chart</span>
    </button>
    <button class="selector-nav-item" onclick="switchMode('table')">
        <i class="fas fa-table"></i>
        <span class="selector-nav-label">Table</span>
    </button>
    <button class="selector-nav-item" onclick="switchMode('raw')">
        <i class="fas fa-code"></i>
        <span class="selector-nav-label">Raw</span>
    </button>
</nav>
```

### Classes

| Class | Element | Purpose |
|-------|---------|---------|
| `.selector-nav` | `<nav>` | Container — vertical flex column, dark background |
| `.selector-nav-item` | `<button>` or `<a>` | Individual item (icon above label, flex column) |
| `.selector-nav-label` | `<span>` | Label text below icon (9px, truncated at 48px) |

### Active Indicator

Set `data-indicator` on the `<nav>` element:

| Value | Effect |
|-------|--------|
| `"left"` | Accent bar on left edge of active item (frame-level, pointing inward) |
| `"right"` | Accent bar on right edge of active item (in-app, pointing into content) |
| _(none)_ | Background highlight only, no edge bar |

Accent color uses `--module-accent-color` (inherited from `[data-module-accent]` on parent), falling back to `--workspace-icon-primary` (default: `#059669` emerald).

### Module Accent Line (Framework-Controlled)

The top-border accent line across the module content area is **framework-controlled** — apps must not add their own accent borders. The framework uses `#main-content[data-module-accent]::before` with `z-index: 100` and `!important` to ensure a continuous, override-proof accent line. See `workspace-sidebar.css` for implementation and `docs/design/workspace-layout.md` for full architecture.

### Active State Management

Toggle `.active` on `.selector-nav-item` elements via JavaScript.
Typical pattern (matches Writer mode selector):

```javascript
function switchMode(mode) {
    // Update nav
    document.querySelectorAll('#myapp-mode-selector .selector-nav-item')
        .forEach(btn => {
            const match = btn.getAttribute('onclick') || '';
            const btnMode = (match.match(/switchMode\('(\w+)'\)/) || [])[1];
            btn.classList.toggle('active', btnMode === mode);
        });
    // Show/hide views
    document.querySelectorAll('.myapp-view').forEach(view => {
        view.hidden = view.dataset.mode !== mode;
    });
}
```

### CSS

Shared styles in `static/shared/css/components/selector-nav.css` (auto-loaded via `common.css`).

### Naming Convention

| ID Pattern | Example | Usage |
|------------|---------|-------|
| `#ws-app-selector` | Frame sidebar | App Selector (`data-indicator="left"`) |
| `#<module>-mode-selector` | `#writer-mode-selector` | In-app mode switcher (`data-indicator="right"`) |

Plugins should follow: `#<module>-<purpose>-selector`.

---

## Collapsible Panel (`.collapsible-panel`)

Any panel can be made collapsible by adding the `.collapsible-panel` class.
When collapsed, the panel shows only its icon and label (horizontal, no rotation).

```html
<div class="my-panel collapsible-panel" data-hide-title-expanded>
    <div class="panel-header">
        <button class="panel-toggle-btn" onclick="togglePanel('.my-panel')">
            <i class="fas fa-chevron-left"></i>
        </button>
        <span class="panel-title"><i class="fas fa-chart-bar"></i> My Panel</span>
    </div>
    <div class="panel-content">...</div>
</div>
```

When collapsed:
- Icon appears on top, label below (vertical flex column, 9px font)
- No `writing-mode` rotation — matches workspace sidebar pattern
- Content area hidden, panel shrinks to ~40px width

---

## Summary: What's Available

| Component | CSS File | Auto-loaded | Use Case |
|-----------|----------|-------------|----------|
| Resizer | `components/resizer.css` | Yes | Split panels with drag resize + collapse |
| Selector Nav | `components/selector-nav.css` | Yes | Vertical icon+label mode switcher |
| Collapsible Panel | `components/collapsible-panel.css` | Yes | Panels that collapse to icon+label |
| Panel Resizer (legacy) | `components/panel-resizer.css` | Yes | Old system — use Resizer instead |

<!-- EOF -->
