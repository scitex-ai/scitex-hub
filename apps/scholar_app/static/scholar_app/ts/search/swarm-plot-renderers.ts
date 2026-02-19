/**
 * Swarm Plot Renderer Functions
 *
 * Plotly-based rendering for year, citations, and impact factor distributions.
 * Each renderer accepts a context object drawn from the SwarmPlots module.
 */

// @ts-ignore - Plotly library types
declare const Plotly: any;

import { getThemeColors } from "./swarm-plot-theme";

/**
 * Minimal context required by all renderers
 */
export interface SwarmRenderContext {
  data: {
    id?: string;
    title?: string;
    year?: number;
    citations?: number;
    impact_factor?: number;
  }[];
  filteredIndices: Set<number>;
  jitterCache: Map<number, number>;
  config: { height: number; hovertemplate: string };
  currentRanges: {
    year: [number, number] | null;
    citations: [number, number] | null;
    impactFactor: [number, number] | null;
  };
  getJitter: (idx: number) => number;
}

/** Shared Plotly options */
const PLOTLY_OPTIONS = { responsive: true, displayModeBar: false };

/**
 * Build marker properties from context for a scatter trace
 */
function buildMarker(ctx: SwarmRenderContext) {
  const theme = getThemeColors();
  return {
    size: ctx.data.map((_, idx) =>
      ctx.filteredIndices.has(idx) ? theme.sizeFiltered : theme.sizeIncluded,
    ),
    color: ctx.data.map((_, idx) =>
      ctx.filteredIndices.has(idx) ? theme.pointFiltered : theme.pointIncluded,
    ),
    line: { width: 0 },
    opacity: ctx.data.map((_, idx) => (ctx.filteredIndices.has(idx) ? 0.4 : 1)),
  };
}

/**
 * Build common layout properties
 */
function buildBaseLayout(
  ctx: SwarmRenderContext,
  xAxisOverrides: Record<string, unknown>,
) {
  const theme = getThemeColors();
  return {
    height: ctx.config.height,
    margin: { l: 30, r: 10, t: 5, b: 20 },
    paper_bgcolor: theme.bg,
    plot_bgcolor: theme.bg,
    xaxis: {
      tickfont: { size: 8, color: theme.text },
      gridcolor: theme.grid,
      linecolor: theme.grid,
      zerolinecolor: theme.grid,
      ...xAxisOverrides,
    },
    yaxis: { visible: false, range: [0, 1] },
    hovermode: "closest",
  };
}

/**
 * Render year distribution swarm plot
 */
export function renderYearSwarmPlot(ctx: SwarmRenderContext): void {
  const container = document.getElementById(
    "yearSwarmPlot",
  ) as HTMLElement | null;
  if (!container) return;

  const theme = getThemeColors();
  const years = ctx.data.map((p) => p.year || 0);
  const jitters = ctx.data.map((_, idx) => ctx.getJitter(idx));

  let minYear: number, maxYear: number;
  if (ctx.currentRanges.year) {
    [minYear, maxYear] = ctx.currentRanges.year;
  } else {
    const valid = years.filter((y) => y > 1900);
    minYear = valid.length > 0 ? Math.min(...valid) : 1990;
    maxYear = valid.length > 0 ? Math.max(...valid) : 2025;
  }

  const trace = {
    type: "scatter",
    mode: "markers",
    x: years,
    y: jitters,
    marker: buildMarker(ctx),
    text: ctx.data.map((p) => p.title || "Unknown"),
    hovertemplate: ctx.config.hovertemplate,
    showlegend: false,
  };

  const layout = buildBaseLayout(ctx, {
    title: { text: "Year", font: { size: 9, color: theme.text } },
    range: [minYear - 2, maxYear + 2],
    dtick: Math.ceil((maxYear - minYear) / 4) || 5,
  });

  // @ts-ignore - Plotly library
  Plotly.newPlot(container, [trace], layout, PLOTLY_OPTIONS);
}

/**
 * Render citations distribution swarm plot
 */
export function renderCitationsSwarmPlot(ctx: SwarmRenderContext): void {
  const container = document.getElementById(
    "citationsSwarmPlot",
  ) as HTMLElement | null;
  if (!container) return;

  const theme = getThemeColors();
  const citations = ctx.data.map((p) => p.citations || 0);
  const jitters = ctx.data.map((_, idx) => ctx.getJitter(idx));

  let maxCitations: number;
  if (ctx.currentRanges.citations) {
    maxCitations = ctx.currentRanges.citations[1];
  } else {
    const valid = citations.filter((c) => c > 0);
    maxCitations = valid.length > 0 ? Math.max(...valid) : 1000;
  }

  const useLog = maxCitations > 1000;

  const trace = {
    type: "scatter",
    mode: "markers",
    x: citations,
    y: jitters,
    marker: buildMarker(ctx),
    text: ctx.data.map((p) => p.title || "Unknown"),
    hovertemplate: ctx.config.hovertemplate,
    showlegend: false,
  };

  const layout = buildBaseLayout(ctx, {
    title: { text: "Citations", font: { size: 9, color: theme.text } },
    type: useLog ? "log" : "linear",
    range: useLog
      ? [0, Math.log10(maxCitations * 1.1)]
      : [0, maxCitations * 1.1],
  });

  // @ts-ignore - Plotly library
  Plotly.newPlot(container, [trace], layout, PLOTLY_OPTIONS);
}

/**
 * Render impact factor distribution swarm plot
 */
export function renderImpactFactorSwarmPlot(ctx: SwarmRenderContext): void {
  const container = document.getElementById(
    "impactFactorSwarmPlot",
  ) as HTMLElement | null;
  if (!container) return;

  const theme = getThemeColors();
  const impactFactors = ctx.data.map((p) => p.impact_factor || 0);
  const jitters = ctx.data.map((_, idx) => ctx.getJitter(idx));

  let maxIF: number;
  if (ctx.currentRanges.impactFactor) {
    maxIF = ctx.currentRanges.impactFactor[1];
  } else {
    const valid = impactFactors.filter((f) => f > 0);
    maxIF = valid.length > 0 ? Math.max(...valid) : 50;
  }

  const trace = {
    type: "scatter",
    mode: "markers",
    x: impactFactors,
    y: jitters,
    marker: buildMarker(ctx),
    text: ctx.data.map((p) => p.title || "Unknown"),
    hovertemplate: ctx.config.hovertemplate,
    showlegend: false,
  };

  const layout = buildBaseLayout(ctx, {
    title: { text: "IF", font: { size: 9, color: theme.text } },
    range: [0, Math.ceil(maxIF * 1.1)],
  });

  // @ts-ignore - Plotly library
  Plotly.newPlot(container, [trace], layout, PLOTLY_OPTIONS);
}
