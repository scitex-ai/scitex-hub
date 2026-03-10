/**
 * StatsTypes - Type definitions for StatsManager
 *
 * Extracted from StatsManager.ts for file-size compliance.
 */

export interface StatContext {
  n_groups: number;
  sample_sizes: number[];
  outcome_type: "continuous" | "ordinal" | "binary" | "categorical";
  design: "between" | "within" | "mixed";
  paired: boolean | null;
  has_control_group: boolean;
  n_factors: number;
  normality_ok: boolean | null;
  variance_homogeneity_ok: boolean | null;
  group_names?: string[];
  control_group_name?: string;
}

export interface TestMenuItem {
  id: string;
  label: string;
  family: string;
  enabled: boolean;
  tooltip: string | null;
  priority: number;
}

export interface SummaryStats {
  group: string;
  n: number;
  mean: number | null;
  sd: number | null;
  sem: number | null;
  median: number | null;
  iqr: number | null;
  q1: number | null;
  q3: number | null;
  minimum: number | null;
  maximum: number | null;
}

export interface EffectSize {
  name: string;
  label: string;
  value: number;
  ci_lower?: number;
  ci_upper?: number;
  note?: string;
}

export interface TestResult {
  test_name: string;
  stat: number | null;
  df: number | null;
  p_raw: number | null;
  p_adj: number | null;
  stars: string;
  effect_size: EffectSize | null;
  summary: SummaryStats[];
  formatted: string;
}

export interface StatAnnotation {
  type: "stat_bracket";
  groups: string[];
  stars: string;
  p_value: number;
  test_name: string;
  effect_size: EffectSize | null;
  formatted: string;
  bracket_style: {
    line_width: number;
    bracket_height: number;
    star_offset: number;
  };
}

export interface GroupData {
  name: string;
  values: number[];
}
