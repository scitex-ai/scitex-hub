# Workspace Layout Rules

> Also available at: http://127.0.0.1:8000/dev/design/workspace-layout/

## Display Rule

```
| Console | Files | Viewer | App Selector (fixed) | Actual App |
```

- All panes must be shown in the display
  - Both sides (Console and Actual App) do not overflow outside the display
- All panes **except App Selector** are collapsible to `48px`
- All vertical separators are smart resizers (HorizontalResizer)

### Console Pane
- Always visible in the display (sticky) — never hidden or scrolled away
- Must not grow tall when other panes have long content — keep height constrained
- Input area must remain easily accessible (when pushed too far down, it becomes hard to reach)

## Global Header & Footer

Both global header and footer are minimizable via:
1. **Toggle button** — click the collapse icon
2. **Smart slider** — drag to resize vertically
3. **Double-click** — double-click on empty space

## App Highlighter System

- **App Selector indicator**: right-side 4px partial bar (~60% height, centered, rounded inner corners)
- **Module accent line**: continuous 4px bar across the top of `#main-content`, framework-controlled
- Each app has a configurable accent color (stored as user preference)
- **Single source of truth**: workspace sets `data-app-accent` on `#main-content`; CSS attribute selectors resolve `--app-accent-color`

### Architecture Principles

1. **Framework-controlled** — accent line is rendered by `workspace-sidebar.css` via `#main-content[data-app-accent]::before`, not by individual apps
2. **Override-proof** — uses `!important` and `z-index: 100` to prevent app-side CSS from hiding or overriding the accent
3. **No inline styles** — color resolution happens purely through CSS attribute selectors (`[data-app-accent="writer"]`), not inline `style` attributes
4. **Continuous line** — single `::before` pseudo-element spans the entire module content area with no gaps at sub-panel boundaries

### CSS Variable Cascade

```css
/* 1. Root defines per-module accent colors */
:root {
  --app-accent-writer:  #059669;   /* emerald */
  --app-accent-scholar: #2563eb;   /* blue */
  --app-accent-vis:     #7c3aed;   /* violet */
  --app-accent-console: #d97706;   /* amber */
}

/* 2. CSS attribute selectors map module name → color variable */
[data-app-accent="writer"]  { --app-accent-color: var(--app-accent-writer); }
[data-app-accent="scholar"] { --app-accent-color: var(--app-accent-scholar); }

/* 3. Framework renders the accent line (workspace-sidebar.css) */
#main-content[data-app-accent]::before {
  content: "" !important;
  position: absolute !important;
  top: 0; left: 0; right: 0;
  height: 4px !important;
  background: var(--app-accent-color, transparent) !important;
  z-index: 100 !important;
  pointer-events: none !important;
}

/* 4. Children inherit --app-accent-color automatically */
.selector-nav-item.active::after {
  background: var(--app-accent-color);
}
```

### Do NOT

- Set `--app-accent-color` via inline `style` attribute — CSS attribute selectors handle it
- Add `border-top` to individual panel headers for accent — use the `::before` on `#main-content`
- Override accent styles from app-side CSS — the framework uses `!important`

## Console Pane

- Always visible (sticky) — never hidden
- Does not expand vertically when other content is long
- Input area must remain accessible (not pushed to bottom)

## Configurable Sizing (Accessibility)

Icon sizes and collapsed widths are user-configurable via CSS custom properties:

```css
:root {
  --ui-nav-icon-size: var(--icon-lg);    /* 20px default */
  --ui-collapsed-pane-width: 48px;
}
```

Cascade chain:
- `colors.css (:root)` → defines `--ui-nav-icon-size`
- `selector-nav.css` → `--selector-nav-icon-size: var(--ui-nav-icon-size)`
- `workspace-three-col.css` → `font-size: var(--selector-nav-icon-size)`
- `collapsible-panel.css` → collapsed width from `--ui-collapsed-pane-width`
- Resizer TS defaults aligned to `48px` threshold

To override per user (future settings UI):
```js
document.documentElement.style.setProperty('--ui-nav-icon-size', '24px');
```

## Unified Resizer Architecture

Two classes sharing a common base at `static/shared/ts/components/resizer/`:

### HorizontalResizer

```html
<div class="h-resizer" data-h-resizer
     data-left=".console-pane" data-right=".files-pane"
     data-icon="fa-terminal" data-title="Console"
     data-most-left data-threshold="48">
</div>
```

### VerticalResizer

```html
<div class="v-resizer" data-v-resizer
     data-top=".global-header" data-bottom=".workspace-body"
     data-icon="fa-chevron-up" data-title="Header"
     data-most-top data-threshold="6">
</div>
```

### Flag Reference

| Flag | Effect |
|------|--------|
| `data-most-left` | Left panel collapses when dragged below threshold |
| `data-most-right` | Right panel collapses when dragged below threshold |
| `data-most-top` | Top panel collapses when dragged below threshold |
| `data-most-bottom` | Bottom panel collapses when dragged below threshold |
| `data-in-app` | In-app resizer: no domino cascade, module-scoped storage |
| `data-threshold` | Collapse threshold in pixels (default: 48) |

### Instance Map

**Frame-Level (4 horizontal + 2 vertical)**
1. Console | Files — `data-most-left`
2. Files | Viewer — both sides collapsible
3. Viewer | App Selector — `data-most-left` (selector fixed)
4. App Selector | App — `data-most-right` (selector fixed)
5. Header — vertical, `data-most-top`
6. Footer — vertical, `data-most-bottom`

**In-App (4 horizontal + 1 vertical)**
1. Writer: editor | preview — `data-most-right`
2. Writer: content | details — `data-most-right`
3. Scholar: main | detail — `data-most-right`
4. Vis: sidebar | canvas — `data-most-left`
5. Repo monitor: feed | filter — vertical, `data-most-bottom`

## Implementation Notes & Lessons Learned

### Architecture Decisions
- 6 resizer implementations consolidated to 2 classes + shared base (~780 lines replacing ~1,564)
- `isInApp` flag separates frame-level (domino cascade) from in-app (independent)
- Data-attribute auto-init: HTML declares config, TS scans `[data-h-resizer]` / `[data-v-resizer]`
- Partial accent bars (60% height `::after`) instead of full-height border for modern look
- Module accent colors as single source of truth on workspace container, not app-side

### Gotchas
- CSS variable cascade: root → component → usage. Missing intermediate variable = broken fallback
- Collapsed pane width must be consistent across CSS (`--ui-collapsed-pane-width`), HTML (`data-threshold`), and TS defaults
- PDF iframe must be hidden during resizer drag (visibility hack) or it swallows mouse events
- Double-rAF needed to suppress CSS transitions during initial layout restore from localStorage
- `position: relative` required on `.selector-nav-item` for `::after` pseudo-element positioning
