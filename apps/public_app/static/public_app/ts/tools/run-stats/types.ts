/**
 * Type definitions for Statistics Calculator
 */

export type WorkflowCategory =
  | "describe"
  | "assume"
  | "compare"
  | "posthoc"
  | "effect"
  | "power"
  | "correct";

export type DataMode =
  | "single" // Single dataset for descriptive stats, normality tests
  | "paired" // Two related datasets (paired t-test, Wilcoxon)
  | "groups" // Multiple independent groups (ANOVA, Kruskal-Wallis)
  | "pvalues" // Array of p-values for correction
  | "params"; // Parameter-based calculations (power, effect size)

export type EndpointType =
  | "describe"
  | "calculate"
  | "effect-size"
  | "posthoc"
  | "power"
  | "correct";

export interface StatsTestConfig {
  id: string;
  name: string;
  category: WorkflowCategory;
  subCategory?: string; // Sub-group label within a category
  dataMode: DataMode;
  description: string;
  endpoint: EndpointType;
  // Optional specific parameters for the test
  dataParams?: string[]; // Column names from function signature
  testName?: string; // For 'calculate' endpoint
  measure?: string; // For 'effect-size' endpoint
  method?: string; // For 'posthoc' or 'correct' endpoint
  testType?: string; // For 'power' endpoint
}

export interface StatsResult {
  success: boolean;
  result: Record<string, any>;
  formatted?: string;
  error?: string;
  figure_base64?: string; // Base64 PNG figure
}

export interface CategoryInfo {
  label: string;
  description: string;
}

export interface RecommendationParams {
  n_groups?: number;
  sample_sizes?: number[];
  outcome_type?: "continuous" | "categorical" | "ordinal";
  design?: "between" | "within" | "mixed";
  paired?: boolean;
  has_control_group?: boolean;
  top_k?: number;
}

export interface PowerParams {
  test_type?: "ttest" | "anova" | "correlation" | "proportion";
  effect_size?: number;
  alpha?: number;
  power?: number;
  n?: number;
  n_groups?: number;
  ratio?: number;
}
