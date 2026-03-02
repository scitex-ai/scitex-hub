/**
 * Canvas module barrel file
 *
 * Exports all specialized canvas managers for easy import
 *
 * Phase 5 refactoring complete - all CanvasManager functionality
 * has been extracted into specialized managers
 */

// Phase 1 - Basic canvas operations
export { GridManager } from './GridManager';
export { ExportManager } from './ExportManager';
export { UndoRedoManager } from './UndoRedoManager';

// Phase 2 - Theme, zoom/pan, and selection
export { ThemeManager } from './ThemeManager';
export { ZoomPanManager } from './ZoomPanManager';
export { SelectionManager } from './SelectionManager';

// Phase 3 - Object manipulation and grouping
export { ObjectManager } from './ObjectManager';
export { TransformManager } from './TransformManager';
export { GroupManager } from './GroupManager';

// Phase 4 - Alignment, snapping, and cropping
export { AlignmentManager } from './AlignmentManager';
export { SnapManager } from './SnapManager';
export { CropManager } from './CropManager';

// Phase 5 - Element selection and context menu
export { ElementSelectionManager } from './ElementSelectionManager';
export { ContextMenuManager } from './ContextMenuManager';

// Phase 5.1 - Element selection helpers (extracted from ElementSelectionManager)
export { HitmapManager } from './HitmapManager';
export type { HitmapElementInfo, HitmapColorMap } from './HitmapManager';
export { ElementHighlighter } from './ElementHighlighter';
export type { HighlightType, HighlightColors } from './ElementHighlighter';
export { HitDetector } from './HitDetector';
export type { HitResult } from './HitDetector';
export { StatsExtractor } from './StatsExtractor';
export type { GroupData, StatsData } from './StatsExtractor';

// Phase 6 - Canvas document resize
export { CanvasResizeManager } from './CanvasResizeManager';

// Phase 7 - Session and bundle management
export { SessionManager } from './SessionManager';
export type { SessionState } from './SessionManager';
export { BundleCanvasManager } from './BundleCanvasManager';

// Phase 8 - Additional utilities
export { NudgeManager } from './NudgeManager';
export { AxisDebugManager } from './AxisDebugManager';
export { initializeCanvas, setupCanvasEventListeners } from './CanvasInitializer';
export type { CanvasManagerRefs, InitCallbacks } from './CanvasInitializer';
