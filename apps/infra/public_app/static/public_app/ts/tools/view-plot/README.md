# Plot Viewer Module

Modular TypeScript implementation of the SciTeX plot viewer.

## Structure

```
plot-viewer/
├── index.ts          # Main entry point and barrel export (41 lines)
├── PlotViewer.ts     # Main PlotViewer class (109 lines)
├── types.ts          # Type definitions and constants (77 lines)
├── data.ts           # CSV parsing and plot detection (122 lines)
├── utils.ts          # Utility functions (64 lines)
├── controls.ts       # UI controls management (133 lines)
├── renderers.ts      # Canvas rendering orchestration (230 lines)
├── plot-drawers.ts   # Individual plot type renderers (99 lines)
└── export.ts         # Export functionality (24 lines)
```

Total: 899 lines (refactored from 593 lines monolithic file)

## File Responsibilities

### types.ts
- TypeScript interfaces and types
- Nature journal color palette
- Default settings constants

### data.ts
- CSV parsing from text
- Plot type detection (line, scatter, bar)
- Demo data generation

### utils.ts
- Tick generation for axes
- Number formatting
- Info panel updates

### controls.ts
- Settings panel management
- Slider and input control handlers
- Settings reset functionality

### renderers.ts
- Canvas setup and configuration
- Plot area calculation and scaling
- Axes and ticks rendering
- Coordinate transformations
- Main rendering orchestration

### plot-drawers.ts
- Line plot rendering
- Scatter plot rendering
- Bar chart rendering
- Modular plot type implementations

### export.ts
- PNG export functionality
- Future: SVG export support

### PlotViewer.ts
- Main orchestrator class
- File reading and parsing coordination
- Event listener setup

### index.ts
- Barrel exports for all modules
- Global function setup for backward compatibility
- DOM ready initialization

## Usage

```typescript
import { PlotViewer } from './plot-viewer/index.js';

// Initialize
const viewer = new PlotViewer('plotCanvas');

// Or use global functions (for backward compatibility)
window.toggleSettingsPanel();
window.updateSetting('width', 50);
window.resetToNatureDefaults();
window.downloadPlot();
window.loadDemoData();
```

## Compilation

From `apps/public_app/static/public_app/`:

```bash
# Type check only
npx tsc --noEmit

# Compile to JavaScript
npx tsc -p tsconfig.json

# Or compile to specific output
npx tsc -p tsconfig.json --outDir ./js
```

## Deployment Note

Due to root-owned files in `js/tools/` directory, manual deployment steps are required:

1. Compile TypeScript files:
   ```bash
   cd apps/public_app/static/public_app
   npx tsc -p tsconfig.json --outDir /tmp/plot-viewer-js
   ```

2. Fix ownership and copy compiled files:
   ```bash
   sudo chown -R ywatanabe:ywatanabe js/tools/
   sudo chmod -R u+w js/tools/
   rm -rf js/tools/plot-viewer
   cp -r /tmp/plot-viewer-js/tools/plot-viewer js/tools/
   ```

3. Or use Docker build process which handles permissions automatically.

## Migration Notes

- Original file: `plot-viewer.ts` (593 lines) → backed up as `plot-viewer.ts.backup`
- HTML template updated to use modular import: `<script type="module" src="...plot-viewer/index.js">`
- All inline event handlers continue to work via global function exports
- No breaking changes to external API

## Backward Compatibility

The module maintains full backward compatibility by exposing global functions:
- `toggleSettingsPanel()`
- `updateSetting(param, value)`
- `resetToNatureDefaults()`
- `downloadPlot()`
- `loadDemoData()`

These are used by inline onclick handlers in the HTML template.
