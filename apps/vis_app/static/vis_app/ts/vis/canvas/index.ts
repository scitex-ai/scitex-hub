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

// Phase 5.1 - Element selection helpers (extracted from ElementSelectionManager)
export { HitmapManager } from './HitmapManager.ts';
export type { HitmapElementInfo, HitmapColorMap } from './HitmapManager.ts';
export { ElementHighlighter } from './ElementHighlighter.ts';
export type { HighlightType, HighlightColors } from './ElementHighlighter.ts';
export { HitDetector } from './HitDetector.ts';
export type { HitResult } from './HitDetector.ts';
export { StatsExtractor } from './StatsExtractor.ts';
export type { GroupData, StatsData } from './StatsExtractor.ts';

// Phase 6 - Canvas document resize
export { CanvasResizeManager } from './CanvasResizeManager.ts';

// Phase 7 - Session and bundle management
export { SessionManager } from './SessionManager.ts';
export type { SessionState } from './SessionManager.ts';
export { BundleCanvasManager } from './BundleCanvasManager.ts';

// Phase 8 - Additional utilities
export { NudgeManager } from './NudgeManager.ts';
export { AxisDebugManager } from './AxisDebugManager.ts';
export { initializeCanvas, setupCanvasEventListeners } from './CanvasInitializer.ts';
export type { CanvasManagerRefs, InitCallbacks } from './CanvasInitializer.ts';
