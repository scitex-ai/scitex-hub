/**
 * Sigma Editor Modules - Central Export Point
 *
 * This file re-exports all Sigma Editor modules for clean imports in the main file.
 */

// Type definitions and constants
export * from './types.ts';

// Manager modules
export { RulersManager } from './RulersManager.ts';
export { CanvasManager } from './CanvasManager.ts';
// DataTableManager from shared module
export { DataTableManager } from '../../../../../../static/shared/ts/components/data-table/DataTableManager.ts';
export { PropertiesManager } from './PropertiesManager.ts';
export { UIManager } from './UIManager.ts';
export { ResizerManager } from './ResizerManager.ts';
export { PlotDataManager } from './PlotDataManager.ts';

// UI modules
export { DataTabManager } from './ui/DataTabManager.ts';
export { CanvasTabManager } from './ui/CanvasTabManager.ts';

// SciTeX integration modules
export { SciTeXEditor } from './SciTeXEditor.ts';
export { FigureDropHandler } from './FigureDropHandler.ts';
export { PlotGallery } from './PlotGallery.ts';
export { GalleryCategories } from './GalleryCategories.ts';

// Element-level selection (Schema v0.3 compatible)
export { ElementSelectionManager, elementSelectionManager } from './ElementSelectionManager.ts';
export type { ElementBbox, ElementBboxes, ElementBboxesMeta, GeometryPx } from './ElementSelectionManager.ts';

// Statistics integration
export { StatsManager, statsManager } from './StatsManager.ts';
export type {
    StatContext,
    TestMenuItem,
    TestResult,
    StatAnnotation,
    GroupData,
    SummaryStats,
    EffectSize,
} from './StatsManager.ts';
