/**
 * CanvasGraph - interactive force-directed citation network on a <canvas>.
 * Pointer Events give one code path for mouse, pen and touch:
 * drag a node, drag the background to pan, wheel or pinch to zoom, tap a node.
 */

import type { NetworkEdge, NetworkNode, Transform } from "./types";
import {
  centerOn,
  fitTransform,
  lerpTransform,
  nodeRadius,
  pinch,
  screenToWorld,
  worldToScreen,
  zoomAt,
  type Point,
} from "./_view-math";
import { layoutStep, seedPositions, type LayoutEdge } from "./_force-layout";
import { drawGraph, readGraphTheme, type GraphTheme } from "./_canvas-draw";

export interface CanvasGraphCallbacks {
  onNodeTap: (node: NetworkNode | null) => void;
}

interface Gesture {
  kind: "pan" | "node" | "pinch";
  node?: NetworkNode;
  start: Point;
  startTime: number;
  moved: boolean;
}

const TAP_SLOP = 6;
const TAP_MS = 500;
const FIT_PAD = 48;

export class CanvasGraph {
  private host: HTMLElement;
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private callbacks: CanvasGraphCallbacks;
  private nodes: NetworkNode[] = [];
  private edges: LayoutEdge[] = [];
  private radii = new Map<NetworkNode, number>();
  private neighbours = new Map<NetworkNode, Set<NetworkNode>>();
  private labelled = new Set<NetworkNode>();
  private transform: Transform = { x: 0, y: 0, k: 1 };
  private width = 0;
  private height = 0;
  private alpha = 0;
  private frame: number | null = null;
  private anim: { from: Transform; to: Transform; start: number } | null = null;
  private selected: NetworkNode | null = null;
  private theme: GraphTheme;
  private pointers = new Map<number, Point>();
  private gesture: Gesture | null = null;
  private observers: { disconnect(): void }[] = [];

  constructor(host: HTMLElement, callbacks: CanvasGraphCallbacks) {
    this.host = host;
    this.callbacks = callbacks;
    host.innerHTML = "";
    this.canvas = document.createElement("canvas");
    this.canvas.className = "citation-graph-canvas";
    this.canvas.setAttribute("role", "img");
    host.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d")!;
    this.theme = readGraphTheme(host);
    this.bind();
    this.resize();
  }

  destroy(): void {
    if (this.frame) cancelAnimationFrame(this.frame);
    this.observers.forEach((o) => o.disconnect());
    this.canvas.remove();
  }

  setAriaLabel(label: string): void {
    this.canvas.setAttribute("aria-label", label);
  }

  setData(nodes: NetworkNode[], edges: NetworkEdge[]): void {
    this.nodes = nodes;
    const byId = new Map(nodes.map((n) => [n.id.toLowerCase(), n]));
    const resolve = (v: string | NetworkNode) =>
      typeof v === "string" ? byId.get(v.toLowerCase()) : v;
    this.edges = [];
    this.neighbours = new Map(nodes.map((n) => [n, new Set<NetworkNode>()]));
    for (const e of edges) {
      const s = resolve(e.source);
      const t = resolve(e.target);
      if (!s || !t || s === t) continue;
      this.edges.push({ source: s, target: t });
      this.neighbours.get(s)!.add(t);
      this.neighbours.get(t)!.add(s);
    }

    const maxCites = Math.max(1, ...nodes.map((n) => n.citation_count || 0));
    this.radii = new Map(
      nodes.map((n) => [
        n,
        nodeRadius(n.citation_count || 0, maxCites, n.is_seed),
      ]),
    );
    const topCited = nodes
      .filter((n) => !n.is_seed)
      .sort((a, b) => (b.citation_count || 0) - (a.citation_count || 0))
      .slice(0, 4);
    this.labelled = new Set([...nodes.filter((n) => n.is_seed), ...topCited]);

    const hasSaved =
      nodes.length > 0 && nodes.every((n) => n.x != null && n.y != null);
    if (!hasSaved) seedPositions(nodes);
    for (const n of nodes) {
      n.vx = 0;
      n.vy = 0;
      n.fx = null;
      n.fy = null;
    }

    this.selected = null;
    this.theme = readGraphTheme(this.host);
    this.alpha = hasSaved ? 0 : 1;
    // Settle before the first paint so the graph appears already readable.
    for (let i = 0; i < (hasSaved ? 0 : 180); i++) this.step();
    this.transform = fitTransform(
      this.points(),
      this.width,
      this.height,
      FIT_PAD,
    );
    this.requestFrame();
  }

  select(node: NetworkNode | null): void {
    this.selected = node;
    this.requestFrame();
  }

  centerOnNode(node: NetworkNode, sheetHeight = 0): void {
    const target = centerOn(
      this.transform,
      { x: node.x || 0, y: node.y || 0 },
      this.width,
      this.height,
      sheetHeight,
      Math.max(this.transform.k, 1),
    );
    this.animateTo(target);
  }

  fit(): void {
    this.animateTo(
      fitTransform(this.points(), this.width, this.height, FIT_PAD),
    );
  }

  zoomBy(factor: number): void {
    const mid = { x: this.width / 2, y: this.height / 2 };
    this.animateTo(zoomAt(this.transform, mid, factor));
  }

  /** Page coordinates of a node, used by the e2e probe to tap it. */
  nodeClientPoint(node: NetworkNode): Point {
    const p = worldToScreen(this.transform, { x: node.x || 0, y: node.y || 0 });
    const rect = this.canvas.getBoundingClientRect();
    return { x: rect.left + p.x, y: rect.top + p.y };
  }

  toDataURL(): string {
    return this.canvas.toDataURL("image/png");
  }

  private points(): Point[] {
    return this.nodes.map((n) => ({ x: n.x || 0, y: n.y || 0 }));
  }

  private animateTo(to: Transform): void {
    this.anim = { from: { ...this.transform }, to, start: performance.now() };
    this.requestFrame();
  }

  private refreshTheme(): void {
    this.theme = readGraphTheme(this.host);
    this.requestFrame();
  }

  private resize(): void {
    const rect = this.host.getBoundingClientRect();
    const w = Math.max(1, Math.round(rect.width));
    const h = Math.max(1, Math.round(rect.height));
    const dpr = window.devicePixelRatio || 1;
    if (this.width > 1 && this.height > 1) {
      this.transform.x += (w - this.width) / 2;
      this.transform.y += (h - this.height) / 2;
    } else if (this.nodes.length) {
      this.transform = fitTransform(this.points(), w, h, FIT_PAD);
    }
    this.width = w;
    this.height = h;
    this.canvas.width = Math.round(w * dpr);
    this.canvas.height = Math.round(h * dpr);
    this.canvas.style.width = `${w}px`;
    this.canvas.style.height = `${h}px`;
    this.requestFrame();
  }

  private bind(): void {
    const c = this.canvas;
    const ro = new ResizeObserver(() => this.resize());
    ro.observe(this.host);
    const mo = new MutationObserver(() => this.refreshTheme());
    mo.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme", "class"],
    });
    this.observers.push(ro, mo);
    window
      .matchMedia?.("(prefers-color-scheme: dark)")
      .addEventListener?.("change", () => this.refreshTheme());

    c.addEventListener("pointerdown", (e) => this.onDown(e));
    c.addEventListener("pointermove", (e) => this.onMove(e));
    c.addEventListener("pointerup", (e) => this.onUp(e));
    c.addEventListener("pointercancel", (e) => this.onUp(e, true));
    c.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();
        this.anim = null;
        const factor = Math.exp(-e.deltaY * 0.0015);
        this.transform = zoomAt(this.transform, this.local(e), factor);
        this.requestFrame();
      },
      { passive: false },
    );
    c.addEventListener("dblclick", (e) =>
      this.animateTo(zoomAt(this.transform, this.local(e), 1.8)),
    );
  }

  private local(e: MouseEvent): Point {
    const rect = this.canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  private hit(screen: Point, pointerType: string): NetworkNode | null {
    const w = screenToWorld(this.transform, screen);
    // Fingers are blunt: widen the target on touch.
    const slop = (pointerType === "touch" ? 14 : 4) / this.transform.k;
    let best: NetworkNode | null = null;
    let bestD = Infinity;
    for (const n of this.nodes) {
      const d = Math.hypot((n.x || 0) - w.x, (n.y || 0) - w.y);
      if (d <= (this.radii.get(n) || 8) + slop && d < bestD) {
        best = n;
        bestD = d;
      }
    }
    return best;
  }

  private onDown(e: PointerEvent): void {
    this.canvas.setPointerCapture?.(e.pointerId);
    const p = this.local(e);
    this.pointers.set(e.pointerId, p);
    this.anim = null;
    if (this.pointers.size === 2) {
      this.releaseNode(this.gesture?.node);
      this.gesture = { kind: "pinch", start: p, startTime: 0, moved: true };
      return;
    }
    const node = this.hit(p, e.pointerType);
    this.gesture = {
      kind: node ? "node" : "pan",
      node: node || undefined,
      start: p,
      startTime: performance.now(),
      moved: false,
    };
    this.canvas.classList.add("is-grabbing");
  }

  private onMove(e: PointerEvent): void {
    const prev = this.pointers.get(e.pointerId);
    const p = this.local(e);
    if (!prev) {
      this.canvas.style.cursor = this.hit(p, e.pointerType)
        ? "pointer"
        : "grab";
      return;
    }
    const g = this.gesture;
    if (!g) return;

    if (g.kind === "pinch" && this.pointers.size === 2) {
      const [idA, idB] = [...this.pointers.keys()];
      const a0 = this.pointers.get(idA)!;
      const b0 = this.pointers.get(idB)!;
      this.pointers.set(e.pointerId, p);
      const a1 = this.pointers.get(idA)!;
      const b1 = this.pointers.get(idB)!;
      this.transform = pinch(this.transform, a0, b0, a1, b1);
      this.requestFrame();
      return;
    }
    this.pointers.set(e.pointerId, p);
    if (!g.moved && Math.hypot(p.x - g.start.x, p.y - g.start.y) < TAP_SLOP) {
      return;
    }
    g.moved = true;

    if (g.kind === "node" && g.node) {
      const w = screenToWorld(this.transform, p);
      g.node.fx = g.node.x = w.x;
      g.node.fy = g.node.y = w.y;
      this.alpha = Math.max(this.alpha, 0.3);
    } else if (g.kind === "pan") {
      this.transform = {
        ...this.transform,
        x: this.transform.x + (p.x - prev.x),
        y: this.transform.y + (p.y - prev.y),
      };
    }
    this.requestFrame();
  }

  private onUp(e: PointerEvent, cancelled = false): void {
    this.pointers.delete(e.pointerId);
    const g = this.gesture;
    if (this.pointers.size > 0) {
      if (g?.kind === "pinch") {
        const [rest] = [...this.pointers.values()];
        this.gesture = { kind: "pan", start: rest, startTime: 0, moved: true };
      }
      return;
    }
    this.canvas.classList.remove("is-grabbing");
    this.gesture = null;
    if (!g) return;
    const quick = performance.now() - g.startTime < TAP_MS;
    if (!cancelled && !g.moved && g.kind !== "pinch" && quick) {
      this.callbacks.onNodeTap(g.node || null);
    }
    if (g.kind === "node") this.releaseNode(g.node);
  }

  private releaseNode(node?: NetworkNode): void {
    if (!node) return;
    node.fx = null;
    node.fy = null;
  }

  private step(): void {
    layoutStep(this.nodes, this.edges, this.radii, this.alpha);
    this.alpha *= 0.985;
  }

  private requestFrame(): void {
    if (this.frame == null) {
      this.frame = requestAnimationFrame(() => this.tick());
    }
  }

  private tick(): void {
    this.frame = null;
    let again = false;
    if (this.alpha > 0.005) {
      this.step();
      again = true;
    }
    if (this.anim) {
      const s = Math.min(1, (performance.now() - this.anim.start) / 320);
      this.transform = lerpTransform(this.anim.from, this.anim.to, s);
      if (s >= 1) this.anim = null;
      else again = true;
    }
    drawGraph(this.ctx, {
      nodes: this.nodes,
      edges: this.edges,
      radii: this.radii,
      neighbours: this.neighbours,
      labelled: this.labelled,
      selected: this.selected,
      transform: this.transform,
      width: this.width,
      height: this.height,
      theme: this.theme,
    });
    if (again) this.requestFrame();
  }
}
