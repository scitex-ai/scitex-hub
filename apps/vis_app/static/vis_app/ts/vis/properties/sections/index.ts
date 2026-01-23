/**
 * Pltz Properties Sections - Re-export all section builders
 */

export { DimensionsSection } from "./DimensionsSection.ts";
export { StyleSection } from "./StyleSection.ts";
export { LabelsSection } from "./LabelsSection.ts";
export { AxisTicksSection } from "./AxisTicksSection.ts";
export { TracesSection } from "./TracesSection.ts";
export { LegendSection } from "./LegendSection.ts";
export { ActionsSection } from "./ActionsSection.ts";

// Re-export types
export type { PltzSize, DimensionsSectionStyle } from "./DimensionsSection.ts";
export type { StyleSectionData } from "./StyleSection.ts";
export type { LabelsSectionSpec } from "./LabelsSection.ts";
export type { AxisTicksSpec, AxisTicksStyle } from "./AxisTicksSection.ts";
export type {
  TraceSpec,
  TraceStyle,
  TracesSectionData,
} from "./TracesSection.ts";
export type { LegendStyle } from "./LegendSection.ts";
