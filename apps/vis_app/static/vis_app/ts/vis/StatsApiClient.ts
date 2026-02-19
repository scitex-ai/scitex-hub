/**
 * StatsApiClient - API communication for statistical testing
 *
 * Extracted from StatsManager.ts for file-size compliance.
 * Handles all fetch calls to the stats API endpoints.
 */

import type {
  StatContext,
  TestMenuItem,
  SummaryStats,
  EffectSize,
  TestResult,
  StatAnnotation,
  GroupData,
} from "./StatsTypes.ts";

/**
 * Get applicable tests for the given context
 */
export async function getApplicableTests(context: StatContext): Promise<{
  items: TestMenuItem[];
  recommended: string[];
  effect_sizes: string[];
  posthoc: string[];
}> {
  const response = await fetch("/vis/api/stats/applicable/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(context),
  });

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || "Failed to get applicable tests");
  }

  return {
    items: data.items,
    recommended: data.recommended,
    effect_sizes: data.effect_sizes,
    posthoc: data.posthoc,
  };
}

/**
 * Run a specific statistical test
 */
export async function runTest(
  testName: string,
  groups: GroupData[],
  options: {
    paired?: boolean;
    correction_method?: string;
  } = {},
): Promise<{ result: TestResult; annotation: StatAnnotation }> {
  const response = await fetch("/vis/api/stats/run/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      test_name: testName,
      groups,
      paired: options.paired ?? false,
      correction_method: options.correction_method,
    }),
  });

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || "Failed to run test");
  }

  return { result: data.result, annotation: data.annotation };
}

/**
 * Run all applicable tests (magic mode)
 */
export async function runAllApplicable(
  groups: GroupData[],
  options: {
    outcome_type?: string;
    design?: string;
    paired?: boolean;
    correction_method?: string;
    include_effect_sizes?: boolean;
  } = {},
): Promise<{
  tests: TestResult[];
  effects: EffectSize[];
  recommended: string;
  inspector_data: any;
}> {
  const response = await fetch("/vis/api/stats/run-all/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      groups,
      outcome_type: options.outcome_type ?? "continuous",
      design: options.design ?? "between",
      paired: options.paired ?? false,
      correction_method: options.correction_method ?? "fdr_bh",
      include_effect_sizes: options.include_effect_sizes ?? true,
    }),
  });

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || "Failed to run tests");
  }

  return {
    tests: data.results.tests,
    effects: data.results.effects,
    recommended: data.results.recommended,
    inspector_data: data.inspector_data,
  };
}

/**
 * Build StatContext from plot data
 */
export async function buildContextFromPlot(
  plotType: string,
  groups: GroupData[],
  metadata: Partial<StatContext> = {},
): Promise<{
  context: StatContext;
  applicable_tests: TestMenuItem[];
  recommended: string[];
  summary: SummaryStats[];
}> {
  const response = await fetch("/vis/api/stats/context/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plot_type: plotType,
      data: { groups },
      metadata,
    }),
  });

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.error || "Failed to build context");
  }

  return {
    context: data.context,
    applicable_tests: data.applicable_tests,
    recommended: data.recommended,
    summary: data.summary,
  };
}
