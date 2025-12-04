/**
 * Sigma Editor Modules - Central Export Point
 *
 * This file re-exports all Sigma Editor modules for clean imports in the main file.
 */

// Type definitions and constants
export * from './types.js';

// Manager modules
export { RulersManager } from './RulersManager.js';
export { CanvasManager } from './CanvasManager.js';
// DataTableManager from shared module
export { DataTableManager } from '../../../../../../static/shared/js/components/data-table/DataTableManager.js';
export { PropertiesManager } from './PropertiesManager.js';
export { UIManager } from './UIManager.js';
export { ResizerManager } from './ResizerManager.js';
export { PlotDataManager } from './PlotDataManager.js';

// UI modules
export { DataTabManager } from './ui/DataTabManager.js';
export { CanvasTabManager } from './ui/CanvasTabManager.js';

// SciTeX integration modules
export { SciTeXEditor } from './SciTeXEditor.js';
export { FigureDropHandler } from './FigureDropHandler.js';
export { PlotGallery } from './PlotGallery.js';
