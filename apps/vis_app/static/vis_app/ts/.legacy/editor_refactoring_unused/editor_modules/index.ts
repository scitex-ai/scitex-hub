/**
 * Editor Module Exports
 * Central export point for all editor modules
 */

// History & State Management
export { HistoryManager } from './history/HistoryManager';
export { AutoSaveManager } from './io/AutoSave';
export type { EditorState } from './io/AutoSave';

// Core Canvas Management
export { CanvasManager } from './core/CanvasManager';

// Data Management
export { DataTableManager } from './data/DataTableManager';

// UI Components
export { PanelLayoutManager } from './ui/PanelLayoutManager';
export { PropertiesPanel } from './ui/PropertiesPanel';
export { RulersManager } from './ui/RulersManager';
export { RulerRenderer, type RulerUnit } from './ui/RulerRenderer';
export { ToolbarManager } from './ui/ToolbarManager';

// Tools
export { BasicShapes } from './tools/BasicShapes';
export { AlignmentTools } from './tools/AlignmentTools';
export { SignificanceMarkers } from './tools/SignificanceMarkers';
export { ScaleBarTools } from './tools/ScaleBarTools';
export { ReferenceGuides } from './tools/ReferenceGuides';
export { ScientificAnnotations } from './tools/ScientificAnnotations';
export { BasicAnnotations } from './tools/BasicAnnotations';
export { AdvancedAnnotations } from './tools/AdvancedAnnotations';

// Features
export { ComparisonMode } from './features/ComparisonMode';
export { PlotIntegration, type PlotData } from './features/PlotIntegration';
export { GalleryManager } from './features/GalleryManager';
export { GalleryData } from './features/GalleryData';
export { GalleryUI } from './features/GalleryUI';

// I/O and File Management
export { FileManager } from './io/FileManager';
export { FileExport } from './io/FileExport';
export { FileSave } from './io/FileSave';
export { VersionControl } from './io/VersionControl';
export { VersionComparison } from './io/VersionComparison';

// Layout
export { GridManager } from './layout/GridManager';
export { GridRenderer } from './layout/GridRenderer';
export { RulerDrawer } from './layout/RulerDrawer';

// Transform
export { ZoomManager } from './transform/ZoomManager';
export { ZoomControls } from './transform/ZoomControls';

// Events
export { KeyboardEvents, type KeyboardHandlers } from './events/KeyboardEvents';
export { MouseEvents } from './events/MouseEvents';

// Utilities
export * from './utils/colors';
export * from './utils/geometry';
export * from './utils/selection';
export * from './utils/validation';

// Types
export * from './types';
