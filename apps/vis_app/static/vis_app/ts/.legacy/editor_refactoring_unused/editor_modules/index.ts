/**
 * Editor Module Exports
 * Central export point for all editor modules
 */

// History & State Management
export { HistoryManager } from './history/HistoryManager.ts';
export { AutoSaveManager } from './io/AutoSave.ts';
export type { EditorState } from './io/AutoSave.ts';

// Core Canvas Management
export { CanvasManager } from './core/CanvasManager.ts';

// Data Management
export { DataTableManager } from './data/DataTableManager.ts';

// UI Components
export { PanelLayoutManager } from './ui/PanelLayoutManager.ts';
export { PropertiesPanel } from './ui/PropertiesPanel.ts';
export { RulersManager } from './ui/RulersManager.ts';
export { RulerRenderer, type RulerUnit } from './ui/RulerRenderer.ts';
export { ToolbarManager } from './ui/ToolbarManager.ts';

// Tools
export { BasicShapes } from './tools/BasicShapes.ts';
export { AlignmentTools } from './tools/AlignmentTools.ts';
export { SignificanceMarkers } from './tools/SignificanceMarkers.ts';
export { ScaleBarTools } from './tools/ScaleBarTools.ts';
export { ReferenceGuides } from './tools/ReferenceGuides.ts';
export { ScientificAnnotations } from './tools/ScientificAnnotations.ts';
export { BasicAnnotations } from './tools/BasicAnnotations.ts';
export { AdvancedAnnotations } from './tools/AdvancedAnnotations.ts';

// Features
export { ComparisonMode } from './features/ComparisonMode.ts';
export { PlotIntegration, type PlotData } from './features/PlotIntegration.ts';
export { GalleryManager } from './features/GalleryManager.ts';
export { GalleryData } from './features/GalleryData.ts';
export { GalleryUI } from './features/GalleryUI.ts';

// I/O and File Management
export { FileManager } from './io/FileManager.ts';
export { FileExport } from './io/FileExport.ts';
export { FileSave } from './io/FileSave.ts';
export { VersionControl } from './io/VersionControl.ts';
export { VersionComparison } from './io/VersionComparison.ts';

// Layout
export { GridManager } from './layout/GridManager.ts';
export { GridRenderer } from './layout/GridRenderer.ts';
export { RulerDrawer } from './layout/RulerDrawer.ts';

// Transform
export { ZoomManager } from './transform/ZoomManager.ts';
export { ZoomControls } from './transform/ZoomControls.ts';

// Events
export { KeyboardEvents, type KeyboardHandlers } from './events/KeyboardEvents.ts';
export { MouseEvents } from './events/MouseEvents.ts';

// Utilities
export * from './utils/colors.ts';
export * from './utils/geometry.ts';
export * from './utils/selection.ts';
export * from './utils/validation.ts';

// Types
export * from './types.ts';
