# SciTeX Vis - Scientific Figure Editor

Canvas-based visual editor for creating publication-quality scientific figures.

## Features

### Current (MVP)
- ✅ Canvas-based editing with Fabric.js
- ✅ Journal presets (Nature, Science, Cell, PNAS)
- ✅ Panel layouts (1×1, 2×1, 1×2, 2×2, 1×3, 3×1)
- ✅ Auto A/B/C/D labels
- ✅ Annotation tools:
  - Text
  - Statistical significance (***)
  - Scale bars
  - Arrows
- ✅ Grid with snap-to-grid
- ✅ Export to PNG/SVG
- ✅ Properties panel
- ✅ Responsive design

### Coming Soon
- Image upload & management
- Save/load figures to database
- PDF export
- Advanced scale bar calibration
- Undo/redo
- Templates library

## Usage

### Access
Navigate to: http://127.0.0.1:8000/vis/

### Quick Start

1. **Select Journal Preset**
   - Choose from dropdown: Nature Single, Science Double, etc.
   - Canvas automatically resizes to exact specifications

2. **Choose Layout**
   - Click layout button: 2×2, 1×3, etc.
   - Panel boundaries and A/B/C/D labels auto-generated

3. **Add Annotations**
   - Click "Text" → Add editable text
   - Click "***" → Add significance marker
   - Click "Scale" → Add scale bar (100 μm)
   - Click "Arrow" → Add directional arrow

4. **Adjust & Refine**
   - Drag objects (snaps to grid)
   - Select objects → Edit in properties panel
   - Double-click text to edit
   - Delete selected object

5. **Export**
   - Click "PNG" → Download high-quality PNG
   - Click "SVG" → Download vector SVG

## Journal Presets

### Nature
- Single: 89mm @ 300dpi, Arial 7pt
- Double: 183mm @ 300dpi, Arial 7pt

### Science
- Single: 87mm @ 300dpi, Arial 8pt
- Double: 180mm @ 300dpi, Arial 8pt

### Cell
- Single: 85mm @ 300dpi, Helvetica 7pt
- Double: 180mm @ 300dpi, Helvetica 7pt

### PNAS
- Single: 87mm @ 300dpi, Arial 6pt
- Double: 180mm @ 300dpi, Arial 6pt

## File Structure

```
apps/vis_app/
├── models.py           # ScientificFigure, FigurePanel, Annotation, etc.
├── views.py            # Django views
├── api_views.py        # REST API endpoints
├── urls.py             # URL routing
├── admin.py            # Admin interface
├── tests.py            # Test suite
├── management/
│   └── commands/
│       └── seed_journal_presets.py
├── templates/vis_app/
│   └── editor.html     # Main editor template
└── static/vis_app/
    ├── css/
    │   └── vis.css     # Styling
    └── ts/
        ├── editor.ts   # Main Canvas editor
        └── types.ts    # TypeScript definitions
```

## API Endpoints

```
GET  /vis/api/presets/                    # List all presets
GET  /vis/api/presets/<id>/               # Get preset details
POST /vis/api/figures/<id>/save/          # Save canvas state
GET  /vis/api/figures/<id>/load/          # Load canvas state
POST /vis/api/figures/<id>/upload-panel/  # Upload panel image
POST /vis/api/figures/<id>/config/        # Update configuration
```

## Development

### Setup Journal Presets
```bash
docker compose -f deployment/docker/docker_dev/docker-compose.yml exec web \
  python manage.py seed_journal_presets
```

### Watch TypeScript
Already running via entrypoint.sh
Log: `tail -f logs/tsc-watch-all.log`

### Test
```bash
docker compose -f deployment/docker/docker_dev/docker-compose.yml exec web \
  python manage.py test apps.vis_app
```

## Technical Details

### Dependencies
- **Backend**: Django, PostgreSQL
- **Frontend**: TypeScript, Fabric.js 5.5.2
- **Styling**: Custom CSS (GitHub-inspired)

### Canvas
- Default size: 1051×709px (89mm @ 300dpi - Nature single)
- Grid: 20px spacing with major/minor lines
- Snap tolerance: 20px

### Export
- PNG: High-quality (quality: 1.0)
- SVG: Vector format (editable in Illustrator)
- Grid automatically hidden during export

## Keyboard Shortcuts (Planned)
- Ctrl+S: Save
- Ctrl+Z: Undo
- Ctrl+Y: Redo
- Delete: Remove selected object
- Ctrl+D: Duplicate
- Ctrl+G: Toggle grid

## Credits
Based on the vision document: `GITIGNORED/VIZ_VISION.md`
Implementation checklist: `GITIGNORED/VIZ_TODO.md`
