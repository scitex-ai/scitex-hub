/**
 * Hover readout for the inline-SVG metric charts.
 *
 * The pre-rendered PNGs this replaced could not be interrogated at all — a
 * reader could see a spike but never its value or its time. Coordinates are
 * mapped with the SVG's own screen CTM, so the readout stays exact under any
 * container width and under `preserveAspectRatio` letterboxing.
 */

import type { ChartPayload } from "./series-client";
import type { ChartGeometry } from "./svg-chart";
import { PLOT_BOX, formatClock, formatValue } from "./svg-chart";

const SVG_NS = "http://www.w3.org/2000/svg";

function makeEl(name: string, attrs: Record<string, string>): SVGElement {
  const el = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attrs)) {
    el.setAttribute(key, value);
  }
  return el;
}

function nearestIndex(
  svg: SVGSVGElement,
  event: PointerEvent,
  count: number,
): number | null {
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const local = new DOMPoint(event.clientX, event.clientY).matrixTransform(
    ctm.inverse(),
  );
  if (local.x < PLOT_BOX.left - 6 || local.x > PLOT_BOX.right + 6) return null;
  const span = PLOT_BOX.right - PLOT_BOX.left;
  const ratio = (local.x - PLOT_BOX.left) / (span || 1);
  const index = Math.round(ratio * (count - 1));
  return Math.min(count - 1, Math.max(0, index));
}

/** Wire pointer tracking onto a rendered chart. Safe to call repeatedly. */
export function attachHover(
  host: HTMLElement,
  chart: ChartPayload,
  timestamps: number[],
  geo: ChartGeometry,
): void {
  const svg = host.querySelector<SVGSVGElement>("svg.svg-chart-canvas");
  if (!svg || timestamps.length === 0) return;

  const group = makeEl("g", { class: "svg-chart-hover", opacity: "0" });
  const guide = makeEl("line", {
    y1: String(PLOT_BOX.top),
    y2: String(PLOT_BOX.bottom),
    stroke: "currentColor",
    "stroke-width": "1",
    "stroke-dasharray": "3 3",
  });
  const readout = makeEl("text", {
    "font-size": "13",
    fill: "currentColor",
    "text-anchor": "middle",
    y: String(PLOT_BOX.top - 14),
  });
  group.appendChild(guide);
  group.appendChild(readout);
  svg.appendChild(group);

  const show = (index: number) => {
    const x = geo.xOf(index);
    guide.setAttribute("x1", x.toFixed(2));
    guide.setAttribute("x2", x.toFixed(2));

    const parts = chart.series
      .map((line) => {
        const value = line.values[index];
        if (value === null || value === undefined) return null;
        const shown = formatValue(value, chart.unit, chart.integer);
        return chart.series.length > 1 ? `${line.label} ${shown}` : shown;
      })
      .filter((part): part is string => part !== null);

    if (parts.length === 0) {
      group.setAttribute("opacity", "0");
      return;
    }

    readout.textContent = `${formatClock(timestamps[index])}  ${parts.join("  ")}`;
    const clamped = Math.min(
      PLOT_BOX.right - 60,
      Math.max(PLOT_BOX.left + 60, x),
    );
    readout.setAttribute("x", clamped.toFixed(2));
    group.setAttribute("opacity", "1");
  };

  svg.addEventListener("pointermove", (event) => {
    const index = nearestIndex(svg, event as PointerEvent, timestamps.length);
    if (index === null) {
      group.setAttribute("opacity", "0");
      return;
    }
    show(index);
  });

  svg.addEventListener("pointerleave", () => {
    group.setAttribute("opacity", "0");
  });
}
