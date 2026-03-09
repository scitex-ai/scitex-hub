/**
 * Pltz Properties Sections - Re-export all section builders
 */

export { DimensionsSection } from "./DimensionsSection";
export { StyleSection } from "./StyleSection";
export { LabelsSection } from "./LabelsSection";
export { AxisTicksSection } from "./AxisTicksSection";
export { TracesSection } from "./TracesSection";
export { LegendSection } from "./LegendSection";
export { ActionsSection } from "./ActionsSection";

// Re-export types
export type { PltzSize, DimensionsSectionStyle } from "./DimensionsSection";
export type { StyleSectionData } from "./StyleSection";
export type { LabelsSectionSpec } from "./LabelsSection";
export type { AxisTicksSpec, AxisTicksStyle } from "./AxisTicksSection";
export type {
  TraceSpec,
  TraceStyle,
  TracesSectionData,
} from "./TracesSection";
export type { LegendStyle } from "./LegendSection";
