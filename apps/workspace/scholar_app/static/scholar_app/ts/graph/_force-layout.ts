/**
 * One tick of the force layout: node repulsion (with a collision floor),
 * springs along citation edges, and a weak pull toward the origin.
 * Pinned nodes (fx/fy) stay put.
 */

import type { NetworkNode } from "./types";

export interface LayoutEdge {
  source: NetworkNode;
  target: NetworkNode;
}

export function layoutStep(
  nodes: NetworkNode[],
  edges: LayoutEdge[],
  radii: Map<NetworkNode, number>,
  alpha: number,
): void {
  const r = (n: NetworkNode) => radii.get(n) || 8;
  for (let i = 0; i < nodes.length; i++) {
    const p = nodes[i];
    for (let j = i + 1; j < nodes.length; j++) {
      const q = nodes[j];
      let dx = (q.x || 0) - (p.x || 0);
      let dy = (q.y || 0) - (p.y || 0);
      let d2 = dx * dx + dy * dy;
      if (d2 < 0.01) {
        dx = (i % 2) - 0.5;
        dy = (j % 2) - 0.5;
        d2 = 0.5;
      }
      const minD = r(p) + r(q) + 6;
      const f = (900 / d2 + (d2 < minD * minD ? 0.4 : 0)) * alpha;
      const d = Math.sqrt(d2);
      const fx = (dx / d) * f;
      const fy = (dy / d) * f;
      p.vx = (p.vx || 0) - fx;
      p.vy = (p.vy || 0) - fy;
      q.vx = (q.vx || 0) + fx;
      q.vy = (q.vy || 0) + fy;
    }
  }
  for (const e of edges) {
    const dx = (e.target.x || 0) - (e.source.x || 0);
    const dy = (e.target.y || 0) - (e.source.y || 0);
    const d = Math.hypot(dx, dy) || 1;
    const rest = 60 + r(e.source) + r(e.target);
    const f = ((d - rest) / d) * 0.06 * alpha;
    e.source.vx = (e.source.vx || 0) + dx * f;
    e.source.vy = (e.source.vy || 0) + dy * f;
    e.target.vx = (e.target.vx || 0) - dx * f;
    e.target.vy = (e.target.vy || 0) - dy * f;
  }
  for (const n of nodes) {
    if (n.fx != null && n.fy != null) {
      n.x = n.fx;
      n.y = n.fy;
      n.vx = 0;
      n.vy = 0;
      continue;
    }
    n.vx = ((n.vx || 0) - (n.x || 0) * 0.012 * alpha) * 0.6;
    n.vy = ((n.vy || 0) - (n.y || 0) * 0.012 * alpha) * 0.6;
    n.x = (n.x || 0) + (n.vx || 0);
    n.y = (n.y || 0) + (n.vy || 0);
  }
}

/** Deterministic golden-angle spiral so every build starts from the same shape. */
export function seedPositions(nodes: NetworkNode[]): void {
  const single = nodes.filter((n) => n.is_seed).length === 1;
  nodes.forEach((n, i) => {
    if (single && n.is_seed) {
      n.x = 0;
      n.y = 0;
      return;
    }
    const rad = 30 * Math.sqrt(i + 1);
    const a = i * 2.39996;
    n.x = rad * Math.cos(a);
    n.y = rad * Math.sin(a);
  });
}
