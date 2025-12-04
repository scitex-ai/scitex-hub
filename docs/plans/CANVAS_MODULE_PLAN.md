# Canvas Module UI/UX Plan

## Overview

This document outlines the plan for implementing `.canvas` files as first-class project assets with multi-canvas support across `/vis/` and `/code/` workspaces.

---

## 1. File Format: `.canvas`

### 1.1 File Structure (JSON)
```json
{
  "version": "1.0",
  "type": "scitex-canvas",
  "metadata": {
    "name": "Figure 1",
    "created": "2025-12-03T12:00:00Z",
    "modified": "2025-12-03T14:30:00Z",
    "author": "username",
    "description": ""
  },
  "canvas": {
    "width": 800,
    "height": 600,
    "unit": "px",
    "dpi": 300,
    "backgroundColor": "#ffffff",
    "showGrid": true,
    "showRulers": true,
    "snapToGrid": false,
    "gridSize": 10
  },
  "viewport": {
    "zoom": 1.0,
    "panX": 0,
    "panY": 0,
    "viewportTransform": [1, 0, 0, 1, 0, 0]
  },
  "objects": [],
  "layers": [
    {"id": "background", "name": "Background", "visible": true, "locked": true},
    {"id": "main", "name": "Main", "visible": true, "locked": false},
    {"id": "annotations", "name": "Annotations", "visible": true, "locked": false}
  ],
  "exports": {
    "lastExport": null,
    "defaultFormat": "png",
    "defaultDpi": 300
  }
}
```

### 1.2 File Extension & MIME Type
- Extension: `.canvas`
- MIME Type: `application/x-scitex-canvas`
- Icon: Custom canvas icon (layered squares)

---

## 2. UI Components

### 2.1 Tab Bar (Consistent with existing patterns)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [• figure1.canvas ×] [figure2.canvas ×] [plot.py ×] [data.csv ×] [+]│
└─────────────────────────────────────────────────────────────────────┘
  ↑ Dirty indicator    ↑ Close button                              ↑ New
```

**CSS Classes** (extend existing):
```css
.file-tab                    /* Base tab */
.file-tab.active             /* Active tab */
.file-tab.canvas-tab         /* Canvas-specific styling */
.file-tab.dirty::before      /* Unsaved indicator dot */
.file-tab-icon               /* File type icon */
.file-tab-name               /* Filename text */
.file-tab-close              /* Close button */
```

**Tab Behavior**:
- Single-click: Switch to canvas
- Double-click: Rename (inline input)
- Middle-click: Close tab
- Drag: Reorder tabs
- Close button: Close with unsaved prompt if dirty

### 2.2 Canvas Toolbar

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Save] [Undo] [Redo] │ [Select] [Pan] [Zoom] │ [Export ▼] │ [⚙] [?]│
└─────────────────────────────────────────────────────────────────────┘
  ↑ File actions         ↑ Tools                 ↑ Export     ↑ Settings
```

**Tool Groups**:
1. **File Actions**: Save (Ctrl+S), Undo (Ctrl+Z), Redo (Ctrl+Shift+Z)
2. **Selection Tools**: Select (V), Pan (H/Space+drag), Zoom (Z/Ctrl+wheel)
3. **Drawing Tools**: Rectangle, Ellipse, Line, Arrow, Text, Image
4. **Export**: PNG, SVG, PDF, TIFF dropdown
5. **Settings**: Canvas properties, Grid toggle, Rulers toggle

**CSS Classes**:
```css
.canvas-toolbar              /* Toolbar container */
.canvas-toolbar-group        /* Tool group with separator */
.canvas-tool-btn             /* Tool button */
.canvas-tool-btn.active      /* Active tool */
.canvas-tool-btn:disabled    /* Disabled state */
.canvas-tool-dropdown        /* Dropdown button */
```

### 2.3 Canvas Area

```
┌──────────────────────────────────────────────────────────────────────┐
│ ┌──┬────────────────────────────────────────────────────────────┬──┐ │
│ │  │                    Horizontal Ruler                        │  │ │
│ ├──┼────────────────────────────────────────────────────────────┼──┤ │
│ │ V│                                                            │ V│ │
│ │ e│                                                            │ e│ │
│ │ r│                      Canvas Content                        │ r│ │
│ │ t│                                                            │ t│ │
│ │  │                                                            │  │ │
│ ├──┼────────────────────────────────────────────────────────────┼──┤ │
│ │  │                    Horizontal Ruler (bottom)               │  │ │
│ └──┴────────────────────────────────────────────────────────────┴──┘ │
│                                                                      │
│ Zoom: [100% ▼]  Position: (120, 45)  Size: 800×600px                │
└──────────────────────────────────────────────────────────────────────┘
```

**CSS Classes**:
```css
.canvas-container            /* Main container */
.canvas-rulers-area          /* 3x3 grid for rulers */
.canvas-ruler-h              /* Horizontal ruler */
.canvas-ruler-v              /* Vertical ruler */
.canvas-ruler-corner         /* Corner squares */
.canvas-viewport             /* Canvas viewport (scrollable) */
.canvas-element              /* Fabric.js canvas element */
.canvas-status-bar           /* Bottom status bar */
```

### 2.4 Properties Panel (Right Side)

```
┌─────────────────────┐
│ Properties     [×]  │
├─────────────────────┤
│ ▼ Canvas            │
│   Width:  [800] px  │
│   Height: [600] px  │
│   Background: [#fff]│
├─────────────────────┤
│ ▼ Selection         │
│   X: [120]  Y: [45] │
│   W: [200]  H: [150]│
│   Rotation: [0°]    │
│   Opacity: [100%]   │
├─────────────────────┤
│ ▼ Fill              │
│   Color: [#336699]  │
│   Opacity: [100%]   │
├─────────────────────┤
│ ▼ Stroke            │
│   Color: [#000000]  │
│   Width: [1] px     │
│   Style: [Solid ▼]  │
├─────────────────────┤
│ ▼ Layers            │
│   [👁] Background   │
│   [👁] Main ←active │
│   [👁] Annotations  │
│   [+ Add Layer]     │
└─────────────────────┘
```

**CSS Classes**:
```css
.canvas-properties           /* Properties panel */
.canvas-props-section        /* Collapsible section */
.canvas-props-header         /* Section header */
.canvas-props-content        /* Section content */
.canvas-props-row            /* Property row */
.canvas-props-label          /* Property label */
.canvas-props-input          /* Property input */
.canvas-layer-item           /* Layer list item */
.canvas-layer-item.active    /* Active layer */
```

### 2.5 Context Menu (Right-click)

**On Canvas Background**:
```
┌─────────────────────────┐
│ Paste                   │
│ Select All              │
├─────────────────────────┤
│ Canvas Properties...    │
│ Export...               │
├─────────────────────────┤
│ Zoom In                 │
│ Zoom Out                │
│ Fit to Window           │
│ Actual Size (100%)      │
└─────────────────────────┘
```

**On Selected Object**:
```
┌─────────────────────────┐
│ Cut           Ctrl+X    │
│ Copy          Ctrl+C    │
│ Paste         Ctrl+V    │
│ Duplicate     Ctrl+D    │
│ Delete        Del       │
├─────────────────────────┤
│ Bring to Front          │
│ Bring Forward           │
│ Send Backward           │
│ Send to Back            │
├─────────────────────────┤
│ Group         Ctrl+G    │
│ Ungroup       Ctrl+U    │
├─────────────────────────┤
│ Properties...           │
└─────────────────────────┘
```

### 2.6 File Tree Integration

**New Context Menu Items** (for .canvas files):
```
Right-click on figure1.canvas:
┌─────────────────────────┐
│ Open                    │
│ Open in New Tab         │
├─────────────────────────┤
│ Export as PNG...        │
│ Export as SVG...        │
│ Export as PDF...        │
├─────────────────────────┤
│ Cut            Ctrl+X   │
│ Copy           Ctrl+C   │
│ Duplicate                │
│ Rename         F2       │
│ Delete         Del      │
├─────────────────────────┤
│ Properties              │
└─────────────────────────┘
```

**New File Dialog** (when creating):
```
┌──────────────────────────────────────┐
│ New Canvas                       [×] │
├──────────────────────────────────────┤
│ Name: [figure1        ] .canvas      │
│                                      │
│ Template:                            │
│   ○ Blank (800×600)                  │
│   ○ A4 Portrait (210×297mm)          │
│   ○ A4 Landscape (297×210mm)         │
│   ○ Letter (8.5×11in)                │
│   ○ Custom...                        │
│                                      │
│ [Cancel]              [Create]       │
└──────────────────────────────────────┘
```

---

## 3. Keyboard Shortcuts

### 3.1 File Operations
| Shortcut | Action |
|----------|--------|
| Ctrl+S | Save canvas |
| Ctrl+Shift+S | Save as... |
| Ctrl+E | Export (opens dialog) |
| Ctrl+W | Close tab |

### 3.2 Edit Operations
| Shortcut | Action |
|----------|--------|
| Ctrl+Z | Undo |
| Ctrl+Shift+Z / Ctrl+Y | Redo |
| Ctrl+X | Cut |
| Ctrl+C | Copy |
| Ctrl+V | Paste |
| Ctrl+D | Duplicate |
| Del / Backspace | Delete |
| Ctrl+A | Select all |
| Escape | Deselect / Cancel |

### 3.3 View Operations
| Shortcut | Action |
|----------|--------|
| Ctrl+0 | Fit to window |
| Ctrl+1 | Actual size (100%) |
| Ctrl++ / Ctrl+= | Zoom in |
| Ctrl+- | Zoom out |
| Ctrl+Wheel | Zoom at cursor |
| Space+Drag | Pan canvas |
| Arrow keys | Nudge selection (1px) |
| Shift+Arrow | Nudge selection (10px) |

### 3.4 Tool Shortcuts
| Shortcut | Tool |
|----------|------|
| V | Select tool |
| H | Pan/Hand tool |
| Z | Zoom tool |
| R | Rectangle |
| E | Ellipse |
| L | Line |
| A | Arrow |
| T | Text |
| I | Insert image |

### 3.5 Object Operations
| Shortcut | Action |
|----------|--------|
| Ctrl+G | Group |
| Ctrl+Shift+G | Ungroup |
| Ctrl+] | Bring forward |
| Ctrl+Shift+] | Bring to front |
| Ctrl+[ | Send backward |
| Ctrl+Shift+[ | Send to back |
| Ctrl+L | Lock/Unlock |

---

## 4. Interactions & Workflows

### 4.1 Opening a Canvas File

```
User double-clicks figure1.canvas in file tree
    ↓
FileTreeManager.onFileClick('figure1.canvas')
    ↓
Check file extension → .canvas
    ↓
CanvasTabManager.openFile('figure1.canvas')
    ↓
If already open → activate existing tab
    ↓
Else → Create new CanvasInstance
    ↓
Load JSON content via API
    ↓
CanvasInstance.loadState(json)
    ↓
Render canvas with Fabric.js
    ↓
Add tab to tab bar
    ↓
Activate tab (show canvas, hide others)
```

### 4.2 Creating a New Canvas

```
User right-clicks in file tree → "New Canvas"
    ↓
Show "New Canvas" modal
    ↓
User enters name + selects template
    ↓
CanvasFileHandler.createNew(name, template)
    ↓
Save new .canvas file to server
    ↓
Refresh file tree
    ↓
Auto-open new canvas in tab
```

### 4.3 Saving a Canvas

```
User presses Ctrl+S or clicks Save
    ↓
CanvasInstance.saveState()
    ↓
Serialize Fabric.js canvas to JSON
    ↓
Update metadata.modified timestamp
    ↓
CanvasFileHandler.save(path, json)
    ↓
API call to write file
    ↓
Clear dirty flag
    ↓
Update tab title (remove dirty dot)
```

### 4.4 Exporting a Canvas

```
User clicks Export → PNG
    ↓
Show export options dialog (DPI, quality)
    ↓
CanvasInstance.export('png', { dpi: 300 })
    ↓
Fabric.js canvas.toDataURL() or toBlob()
    ↓
If save to file:
    → API call to save alongside .canvas
    → figure1.png created
    ↓
If download:
    → Trigger browser download
```

### 4.5 Auto-save Flow

```
Any canvas modification
    ↓
CanvasInstance.markDirty()
    ↓
Update tab title with "•" prefix
    ↓
Debounce timer starts (5 seconds)
    ↓
If no changes in 5s → auto-save
    ↓
CanvasFileHandler.save()
    ↓
Clear dirty flag
```

### 4.6 Tab Switching

```
User clicks different canvas tab
    ↓
CanvasTabManager.activateTab(tabId)
    ↓
Current canvas remains in DOM (hidden)
    ↓
New canvas container shown (display: block)
    ↓
Focus transferred to new canvas
    ↓
Properties panel updates for new selection
    ↓
Toolbar state updates (undo/redo availability)
```

### 4.7 Closing Tab with Unsaved Changes

```
User clicks × on dirty tab
    ↓
Check if canvas.isDirty()
    ↓
Show confirmation modal:
    "Save changes to figure1.canvas?"
    [Don't Save] [Cancel] [Save]
    ↓
Don't Save → close without saving
Cancel → abort close
Save → save then close
    ↓
CanvasTabManager.closeTab(tabId)
    ↓
CanvasInstance.dispose()
    ↓
Remove tab from tab bar
    ↓
Activate adjacent tab (or show empty state)
```

---

## 5. State Management

### 5.1 Tab State
```typescript
interface CanvasTabState {
  id: string;              // File path
  name: string;            // Display name
  dirty: boolean;          // Has unsaved changes
  lastSaved: Date | null;  // Last save timestamp
}
```

### 5.2 Canvas Instance State
```typescript
interface CanvasInstanceState {
  document: CanvasDocument;     // Parsed .canvas JSON
  fabricCanvas: fabric.Canvas;  // Fabric.js instance
  history: HistoryManager;      // Undo/redo
  selection: fabric.Object[];   // Current selection
  activeTool: ToolType;         // Current tool
  activeLayer: string;          // Current layer ID
}
```

### 5.3 Persistence
- **LocalStorage**: Tab order, last active tab, tool preferences
- **Server**: .canvas file content, exported images
- **Session**: Undo history (not persisted across reload)

---

## 6. Implementation Phases

### Phase 1: Core Canvas Module (Week 1)
- [ ] Create `CanvasDocument` type and parser
- [ ] Create `CanvasFileHandler` for load/save
- [ ] Extract `CanvasCore` from vis_app (Fabric.js wrapper)
- [ ] Create `RulerCore` (stateless ruler renderer)
- [ ] Basic canvas rendering without tools

### Phase 2: Multi-Tab Support (Week 1-2)
- [ ] Create `CanvasInstance` class
- [ ] Create `CanvasTabManager` extending shared patterns
- [ ] Tab bar UI with file-tab consistency
- [ ] Tab switching with DOM hiding (not destruction)
- [ ] Dirty state tracking and display

### Phase 3: File Integration (Week 2)
- [ ] Register .canvas handler in file tree
- [ ] Context menu for .canvas files
- [ ] "New Canvas" dialog and flow
- [ ] Double-click to open in tab
- [ ] Auto-save implementation

### Phase 4: Toolbar & Tools (Week 2-3)
- [ ] Canvas toolbar UI
- [ ] Tool system (select, pan, zoom)
- [ ] Drawing tools (rect, ellipse, line, text)
- [ ] Keyboard shortcuts
- [ ] Undo/redo with history manager

### Phase 5: Properties Panel (Week 3)
- [ ] Properties panel UI
- [ ] Canvas properties section
- [ ] Selection properties section
- [ ] Layer management section
- [ ] Property binding to selection

### Phase 6: Export & Polish (Week 3-4)
- [ ] Export dialog UI
- [ ] PNG/SVG/PDF export implementation
- [ ] Context menus (canvas + object)
- [ ] Zoom controls and status bar
- [ ] Theme support (dark/light)

### Phase 7: Integration (Week 4)
- [ ] Integrate with /vis/ workspace
- [ ] Integrate with /code/ workspace
- [ ] Unified tab bar across file types
- [ ] Cross-app consistency testing

---

## 7. File Structure

```
static/shared/ts/components/canvas/
├── core/
│   ├── CanvasCore.ts           # Fabric.js wrapper
│   ├── RulerCore.ts            # Ruler rendering
│   ├── HistoryManager.ts       # Undo/redo
│   └── types.ts                # Shared types
├── document/
│   ├── CanvasDocument.ts       # Document model
│   ├── CanvasFileHandler.ts    # Load/save operations
│   └── CanvasSerializer.ts     # JSON serialization
├── instance/
│   ├── CanvasInstance.ts       # Single canvas manager
│   ├── CanvasTabManager.ts     # Multi-tab coordinator
│   └── CanvasToolManager.ts    # Tool state management
├── ui/
│   ├── CanvasToolbar.ts        # Toolbar component
│   ├── CanvasProperties.ts     # Properties panel
│   ├── CanvasStatusBar.ts      # Status bar
│   ├── CanvasContextMenu.ts    # Context menus
│   └── CanvasExportDialog.ts   # Export dialog
├── tools/
│   ├── SelectTool.ts           # Selection tool
│   ├── PanTool.ts              # Pan/hand tool
│   ├── ZoomTool.ts             # Zoom tool
│   ├── RectTool.ts             # Rectangle tool
│   ├── EllipseTool.ts          # Ellipse tool
│   ├── LineTool.ts             # Line tool
│   ├── ArrowTool.ts            # Arrow tool
│   ├── TextTool.ts             # Text tool
│   └── ImageTool.ts            # Image insert tool
└── index.ts                    # Public exports

static/shared/css/components/canvas/
├── canvas-core.css             # Core canvas styles
├── canvas-toolbar.css          # Toolbar styles
├── canvas-properties.css       # Properties panel
├── canvas-rulers.css           # Ruler styles
├── canvas-tabs.css             # Tab styles (extends file-tabs)
├── canvas-context-menu.css     # Context menu styles
└── index.css                   # Import all
```

---

## 8. API Endpoints

### 8.1 File Operations
```
GET  /api/files/read?path=<path>           # Read .canvas file
POST /api/files/write                       # Save .canvas file
POST /api/files/create                      # Create new .canvas
DELETE /api/files/delete?path=<path>        # Delete file
```

### 8.2 Export Operations
```
POST /api/canvas/export
  Body: { path: string, format: 'png'|'svg'|'pdf', options: {...} }
  Response: { exportPath: string } or blob download
```

### 8.3 Image Upload (for canvas images)
```
POST /api/canvas/upload-image
  Body: FormData with image file
  Response: { path: string, url: string }
```

---

## 9. Success Criteria

- [ ] .canvas files appear with custom icon in file tree
- [ ] Double-click opens canvas in tab
- [ ] Multiple canvas tabs can be open simultaneously
- [ ] Tab switching is instant (no reload delay)
- [ ] Dirty state shows dot prefix in tab title
- [ ] Auto-save after 5 seconds of inactivity
- [ ] Ctrl+S saves immediately
- [ ] Undo/redo works correctly (50 levels)
- [ ] Export produces correct PNG/SVG/PDF
- [ ] Works in both /vis/ and /code/ workspaces
- [ ] Dark/light theme support
- [ ] All keyboard shortcuts functional
- [ ] Properties panel updates on selection change
- [ ] Rulers show correct measurements
- [ ] Zoom/pan works smoothly

---

## 10. Open Questions

1. **Asset embedding vs references**: Should images be embedded in .canvas (base64) or referenced by path?
   - Recommendation: Reference by relative path, with option to embed for portability

2. **Collaborative editing**: Should we support real-time collaboration on canvas files?
   - Recommendation: Defer to future phase, focus on single-user first

3. **Version history**: Should we track version history within the .canvas file?
   - Recommendation: Rely on Git for history, don't duplicate in file

4. **Template library**: Where should canvas templates be stored?
   - Recommendation: `/static/shared/canvas-templates/` or project-level `.scitex/templates/`

---

*Last updated: 2025-12-03*
*Author: Claude Code*
