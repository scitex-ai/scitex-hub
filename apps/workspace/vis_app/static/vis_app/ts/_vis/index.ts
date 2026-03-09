/**
 * Vis Editor Modules - Central Export Point
 *
 * This file re-exports all Vis Editor modules for clean imports in the main file.
 */

// Type definitions and constants
export * from "./types";

// Manager modules
export { RulersManager } from "./RulersManager";
export { CanvasManager } from "./CanvasManager";
// DataTableManager from shared module
export { DataTableManager } from "@/components/data-table/DataTableManager";
export { PropertiesManager } from "./PropertiesManager";
export { UIManager } from "./UIManager";
// ResizerManager removed — migrated to unified resizer (data-h-resizer)
export { PlotDataManager } from "./PlotDataManager";

// UI modules
export { DataTabManager } from "./ui/DataTabManager";
export { CanvasTabManager } from "./ui/CanvasTabManager";

// SciTeX integration modules
export { SciTeXEditor } from "./SciTeXEditor";
export { FigureDropHandler } from "./FigureDropHandler";
export { PlotGallery } from "./PlotGallery";
export { GalleryCategories } from "./GalleryCategories";

// Element-level selection (Schema v0.3 compatible)
export {
  ElementSelectionManager,
  elementSelectionManager,
} from "./ElementSelectionManager";
export type {
  ElementBbox,
  ElementBboxes,
  ElementBboxesMeta,
  GeometryPx,
} from "./ElementSelectionManager";

// Statistics integration
export { StatsManager, statsManager } from "./StatsManager";
export type {
  StatContext,
  TestMenuItem,
  TestResult,
  StatAnnotation,
  GroupData,
  SummaryStats,
  EffectSize,
} from "./StatsManager";

// Bundle managers (pltz/figz)
export { PltzBundleManager, pltzBundleManager } from "./PltzBundleManager";
export { FigzBundleManager, figzBundleManager } from "./FigzBundleManager";

// Bundle UI components
export { BundleGalleryPanel } from "./ui/BundleGalleryPanel";
export type {
  BundleType,
  BundleGalleryPanelOptions,
} from "./ui/BundleGalleryPanel";
export { FigureComposer } from "./ui/FigureComposer";
export type { FigureComposerOptions } from "./ui/FigureComposer";
