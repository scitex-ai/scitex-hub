/**
 * Canvas module barrel file
 *
 * Exports all specialized canvas managers for easy import
 *
 * Phase 5 refactoring complete - all CanvasManager functionality
 * has been extracted into specialized managers
 */

// Phase 1 - Basic canvas operations
export { GridManager } from './GridManager.ts';
export { ExportManager } from './ExportManager.ts';
export { UndoRedoManager } from './UndoRedoManager.ts';

// Phase 2 - Theme, zoom/pan, and selection
export { ThemeManager } from './ThemeManager.ts';
export { ZoomPanManager } from './ZoomPanManager.ts';
export { SelectionManager } from './SelectionManager.ts';

// Phase 3 - Object manipulation and grouping
export { ObjectManager } from './ObjectManager.ts';
export { TransformManager } from './TransformManager.ts';
export { GroupManager } from './GroupManager.ts';

// Phase 4 - Alignment, snapping, and cropping
export { AlignmentManager } from './AlignmentManager.ts';
export { SnapManager } from './SnapManager.ts';
export { CropManager } from './CropManager.ts';

// Phase 5 - Element selection and context menu
export { ElementSelectionManager } from './ElementSelectionManager.ts';
export { ContextMenuManager } from './ContextMenuManager.ts';
