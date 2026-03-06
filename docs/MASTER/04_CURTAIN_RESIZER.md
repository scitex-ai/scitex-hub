<!-- ---
!-- Timestamp: 2026-03-07 07:18:57
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/MASTER/04_CURTAIN_RESIZER.md
!-- --- -->

# Curtain Resizer Specification

Every vertical divider in the workspace is a **curtain** — grab it and slide.
Panels to one side expand, panels to the other side shrink.
No panel ever disappears suddenly. No dead zones. No inconsistency.

## 1. Core Principles

### 1.1 Every pane border is draggable
- Every vertical boundary between panes MUST have a resizer
- Both sides of every fixed-width element (Apps nav, mode selector) MUST respond to drag
- No "dead" borders — if you can see it, you can drag it

### 1.2 Curtain metaphor
- Dragging a resizer is like sliding a curtain along a rail
- Everything on one side expands, everything on the other side contracts
- Fixed-width elements (Apps nav, mode selector) act as curtain handles:
  they don't resize themselves, but propagate force to the nearest resizable neighbor

### 1.3 Gradual, predictable sizing
- Panels shrink/grow smoothly — never jump or disappear
- Minimum width enforced: no panel goes below `thresholdPx` (default 40-48px)
- Maximum width enforced: no panel grows beyond `totalAvailable - threshold`
- Only explicit collapse (below threshold during drag) triggers panel collapse

### 1.4 Magnetic snap
- Resizers snap to percentage-based points (20%, 25%, 33%, 50%, 67%, 75%, 80%)
- Physics model: outer radius 32px (feel the pull), inner radius 8px (lock on)
- Quadratic easing between outer and inner radius
- Visual feedback: `.snapped` class flashes green on the resizer line

## 2. Two Resizer Systems

### 2.1 New System (unified, preferred)
- **Module**: `static/shared/ts/components/resizer/`
- **Classes**: `HorizontalResizer`, `VerticalResizer`
- **HTML**: `<div class="h-resizer" data-h-resizer data-left=".a" data-right=".b">`
- **Auto-init**: elements with `data-h-resizer`/`data-v-resizer` are initialized on DOMContentLoaded
- **Features**: collapse, cascade propagation, magnetic snap, toggle buttons, localStorage persistence
- **Used by**: Writer details resizer, worktree vertical split, any app plugin

### 2.2 Legacy System (workspace-level panels)
- **Module**: `static/shared/ts/components/_workspace-panel-resizer/`
- **HTML**: `<div class="panel-resizer" data-panel-resizer data-target="#panel-id">`
- **Features**: collapse, curtain propagation, magnetic snap, domino cascade
- **Used by**: AI pane, Worktree pane, Viewer pane, Apps pane resizers

### 2.3 Shared utilities
- `_snap.ts`: `magneticSnap()`, `percentSnapPoints()` — used by both systems
- `_cascade.ts`: `getMaxAllowedWidth()`, `findAdjacentPanel()` — workspace-level cascade

## 3. Curtain Handle (Fixed-Width Panels)

Fixed-width panels like the Apps nav (56px) and Writer mode-selector (50px)
don't resize themselves. They are **curtain handles**.

### 3.1 Behavior
- Resizer on a `data-fixed-width` panel skips primary resize
- Propagation always targets the `resizeDirection` side (not drag delta direction)
- Drag delta sign naturally handles shrink vs grow:
  - Drag toward the neighbor panel: shrinks it
  - Drag away from the neighbor panel: grows it (un-collapses if needed)
- Collapsed panels are included in curtain propagation and un-collapsed automatically

### 3.2 Configuration
```html
<div class="panel-resizer" data-panel-resizer
     data-target="#ws-apps-sidebar"
     data-direction="left"
     data-fixed-width
     data-min-width="56"
     data-storage-key="ws-apps-width">
</div>
```

### 3.3 Example: Apps pane
```
Layout: [AI] [Worktree] [Viewer] [Apps 56px] [Module flex:1]

Drag Apps resizer LEFT  → Viewer shrinks, Module (flex:1) auto-expands
Drag Apps resizer RIGHT → Viewer grows,   Module (flex:1) auto-shrinks
```

## 4. In-App Resizers (Writer Layout)

The Writer has its own internal split view with special requirements.

### 4.1 Layout
```
.writer-workspace
├── .writer-container
│   └── .split-view
│       ├── .latex-panel          (flex: 1 1 50%)
│       ├── #writer-editor-resizer (h-resizer, programmatic init)
│       ├── #writer-mode-selector  (50px fixed, curtain handle)
│       └── .preview-panel         (flex: 1 1 50%)
├── #writer-details-resizer        (h-resizer, declarative)
└── .writer-details
```

### 4.2 PDF-aware resizer hooks
The writer-editor-resizer has special PDF handling:
- `onDragStart`: hides PDF iframe (`visibility: hidden`) to prevent render stuttering
- `onDragEnd`: shows iframe + calls `pdfViewer.fitWidth()` to recalculate zoom
- This is why it uses **programmatic init** (not declarative `data-h-resizer`)

### 4.3 Mode selector as curtain handle
The mode selector (50px) sits between the h-resizer and the preview panel.
It should behave as a curtain handle — dragging near it should resize
the LaTeX/preview split without the mode selector itself moving.

**Current issue**: The h-resizer is on the LEFT side of the mode selector,
so only the left side has resize feedback. The right side has no resizer.

**Solution**: Either:
- (a) Add a second resizer on the right side of the mode selector, or
- (b) Make the mode selector itself a curtain handle (like the Apps pane)

Option (b) is preferred as it reuses the curtain pattern. The mode selector
would need a thin resizer overlay on each edge, both controlling the same
latex/preview split but from opposite sides.

## 5. Size Constraints

### 5.1 Minimum width (`thresholdPx`)
- Every panel has a minimum size (default 40-48px)
- When dragged below threshold, the panel collapses (adds `.collapsed` class)
- Below-threshold size is never rendered — it's collapse or threshold, nothing between

### 5.2 Maximum width
- Default: `totalAvailable - threshold` (protects the opposite panel)
- Optional: `data-max-width="600"` for explicit cap (not yet implemented)
- Both the `secondCan && !firstCan` and `firstCan && !secondCan` branches
  in `applyResize()` enforce: `Math.min(newSize, totalSize - threshold)`

### 5.3 Module pane (flex:1) auto-adjustment
- The module pane (`ws-module-pane`) uses `flex: 1` — no explicit width
- When sidebar panels grow/shrink, the module pane auto-adjusts
- Minimum enforced via `min-width: var(--ui-collapsed-pane-width, 48px)`

## 6. Cascade (Domino) Propagation

When a panel collapses during drag, remaining delta transfers to the next panel.

### 6.1 Trigger
- Panel size drops below `thresholdPx` → collapse instantly (during drag, not on mouseUp)
- Find next non-collapsed resizable panel in the same direction
- Continue resizing that panel with remaining delta

### 6.2 Chain
```
Drag AI resizer right →
  AI panel collapses →
    Force transfers to Worktree →
      Worktree collapses →
        Force transfers to Viewer →
          Viewer shrinks (module auto-expands)
```

### 6.3 Limitations
- Cascade only works at workspace level (`isInApp: false`)
- In-app resizers (Writer split) do NOT cascade — they clamp at threshold

## 7. Visual Feedback

### 7.1 Resizer line
- Default: 2px wide, `var(--workspace-border-default)` color
- Hover/active: green `var(--workspace-icon-primary, #059669)`
- Hit area: 26px wide (12px each side via `::before` pseudo-element)

### 7.2 Snap feedback
- `.snapped` class: brief green flash when magnetic snap engages
- Transition: 0.05s ease for responsive feel

### 7.3 Cursor
- `col-resize` during horizontal drag
- `row-resize` during vertical drag
- Applied to `document.body` during drag for consistent feedback

## 8. State Persistence

All resizer states are saved to localStorage:
- Panel sizes: `localStorage[storageKey] = "320"` (px)
- Collapse states: `localStorage[storageKey + "-collapsed"] = "true"`
- Restored on page load via `restoreState()` / `restoreWidth()`

## 9. Implementation Checklist

- [x] Magnetic snap (`_snap.ts`)
- [x] Max-size cap in `applyResize()` — prevents panel disappearance
- [x] Curtain handle for Apps pane (`data-fixed-width` + `resizeDirection`)
- [x] Un-collapse during curtain drag
- [ ] Mode selector as curtain handle (needs second resizer or overlay)
- [ ] `data-max-width` attribute for explicit maximum
- [ ] Scroll-snap for list panes (CSS-only, `scroll-snap-type: y proximity`)
- [ ] Files pane double border fix (`workspace-three-col.css`)

## 10. Files Reference

| File | Role |
|------|------|
| `static/shared/ts/components/resizer/_snap.ts` | Magnetic snap utility |
| `static/shared/ts/components/resizer/_drag-handler.ts` | Drag state machine (new system) |
| `static/shared/ts/components/resizer/_base.ts` | Base class with state management |
| `static/shared/ts/components/resizer/_horizontal.ts` | Horizontal resizer + cascade |
| `static/shared/ts/components/resizer/_vertical.ts` | Vertical resizer |
| `static/shared/ts/components/resizer/_state.ts` | localStorage persistence |
| `static/shared/ts/components/resizer/_toggle.ts` | Toggle button icons |
| `static/shared/ts/components/resizer/_cascade.ts` | Workspace cascade helpers |
| `static/shared/ts/components/_workspace-panel-resizer/resizer.ts` | Legacy resizer (workspace panels) |
| `static/shared/css/components/resizer.css` | Shared resizer styles |

<!-- EOF -->
