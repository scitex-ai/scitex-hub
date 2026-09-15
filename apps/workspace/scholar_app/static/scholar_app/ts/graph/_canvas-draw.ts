/**
 * Paints the citation network onto a 2D context in world coordinates.
 * Colours come from CSS custom properties so light/dark themes apply.
 */

import type { NetworkNode, Transform } from "./types";
import type { LayoutEdge } from "./_force-layout";

export interface GraphTheme {
  edge: string;
  edgeActive: string;
  node: string;
  nodeStroke: string;
  seed: string;
  selected: string;
  label: string;
  halo: string;
  fontFamily: string;
}

export function readGraphTheme(el: Element): GraphTheme {
  const s = getComputedStyle(el);
  const v = (name: string, fallback: string) =>
    s.getPropertyValue(name).trim() || fallback;
  return {
    edge: v("--cg-edge", "rgba(30,58,138,0.22)"),
    edgeActive: v("--cg-edge-active", "rgba(30,58,138,0.85)"),
    node: v("--cg-node", "#7b93c6"),
    nodeStroke: v("--cg-node-stroke", "#ffffff"),
    seed: v("--cg-seed", "#1e3a8a"),
    selected: v("--cg-selected", "#f59e0b"),
    label: v("--cg-label", "#0f172a"),
    halo: v("--cg-halo", "rgba(255,255,255,0.85)"),
    // Canvas does not inherit page fonts; reuse the page's stack (JP fallback included).
    fontFamily: `${s.fontFamily || "sans-serif"}, "Hiragino Sans", "Noto Sans JP", sans-serif`,
  };
}

export interface DrawState {
  nodes: NetworkNode[];
  edges: LayoutEdge[];
  radii: Map<NetworkNode, number>;
  neighbours: Map<NetworkNode, Set<NetworkNode>>;
  labelled: Set<NetworkNode>;
  selected: NetworkNode | null;
  transform: Transform;
  width: number;
  height: number;
  theme: GraphTheme;
}

export function drawGraph(ctx: CanvasRenderingContext2D, st: DrawState): void {
  const { theme, transform: t, selected: sel } = st;
  const dpr = window.devicePixelRatio || 1;
  const radius = (n: NetworkNode) => st.radii.get(n) || 8;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, st.width, st.height);
  ctx.setTransform(dpr * t.k, 0, 0, dpr * t.k, dpr * t.x, dpr * t.y);
  const near = sel ? st.neighbours.get(sel) : null;

  ctx.lineCap = "round";
  for (const e of st.edges) {
    const active = !!sel && (e.source === sel || e.target === sel);
    ctx.strokeStyle = active ? theme.edgeActive : theme.edge;
    ctx.fillStyle = ctx.strokeStyle;
    ctx.lineWidth = (active ? 2 : 1) / t.k;
    ctx.globalAlpha = sel && !active ? 0.35 : 1;
    drawArrow(ctx, e.source, e.target, radius(e.target), t.k);
  }

  for (const n of st.nodes) {
    const r = radius(n);
    ctx.globalAlpha = sel && n !== sel && !near?.has(n) ? 0.35 : 1;
    ctx.beginPath();
    ctx.arc(n.x || 0, n.y || 0, r, 0, Math.PI * 2);
    ctx.fillStyle = n.is_seed ? theme.seed : theme.node;
    ctx.fill();
    ctx.lineWidth = 1.5 / t.k;
    ctx.strokeStyle = theme.nodeStroke;
    ctx.stroke();
    if (n === sel || n.is_seed) {
      ctx.beginPath();
      ctx.arc(n.x || 0, n.y || 0, r + 4 / t.k, 0, Math.PI * 2);
      ctx.lineWidth = (n === sel ? 3 : 2) / t.k;
      ctx.strokeStyle = n === sel ? theme.selected : theme.seed;
      ctx.stroke();
    }
  }
  ctx.globalAlpha = 1;

  const fontPx = 12 / t.k;
  ctx.font = `600 ${fontPx.toFixed(3)}px ${theme.fontFamily}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.lineJoin = "round";
  // Selected first, then seeds and top-cited, so they win label collisions.
  const rank = (n: NetworkNode) =>
    n === sel ? 0 : st.labelled.has(n) ? 1 : near?.has(n) ? 2 : 3;
  const candidates = st.nodes
    .filter((n) => n.title && (rank(n) < 3 || t.k > 1.6))
    .sort((a, b) => rank(a) - rank(b));
  const placed: [number, number, number, number][] = [];
  for (const n of candidates) {
    const text = n.title.length > 30 ? `${n.title.slice(0, 28)}…` : n.title;
    const y = (n.y || 0) + radius(n) + 4 / t.k;
    const w = ctx.measureText(text).width;
    const box: [number, number, number, number] = [
      (n.x || 0) - w / 2,
      y,
      (n.x || 0) + w / 2,
      y + fontPx * 1.2,
    ];
    const clash = placed.some(
      (b) => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1],
    );
    if (clash && n !== sel) continue;
    placed.push(box);
    ctx.lineWidth = 3 / t.k;
    ctx.strokeStyle = theme.halo;
    ctx.strokeText(text, n.x || 0, y);
    ctx.fillStyle = theme.label;
    ctx.fillText(text, n.x || 0, y);
  }
}

/** Citing -> cited, arrowhead stopping at the cited node's rim. */
function drawArrow(
  ctx: CanvasRenderingContext2D,
  s: NetworkNode,
  d: NetworkNode,
  targetRadius: number,
  k: number,
): void {
  const sx = s.x || 0;
  const sy = s.y || 0;
  const dx = (d.x || 0) - sx;
  const dy = (d.y || 0) - sy;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const ex = (d.x || 0) - ux * (targetRadius + 2 / k);
  const ey = (d.y || 0) - uy * (targetRadius + 2 / k);
  ctx.beginPath();
  ctx.moveTo(sx, sy);
  ctx.lineTo(ex, ey);
  ctx.stroke();
  const h = 6 / k;
  ctx.beginPath();
  ctx.moveTo(ex, ey);
  ctx.lineTo(ex - ux * h - uy * h * 0.6, ey - uy * h + ux * h * 0.6);
  ctx.lineTo(ex - ux * h + uy * h * 0.6, ey - uy * h - ux * h * 0.6);
  ctx.closePath();
  ctx.fill();
}
