/**
 * GraphInteraction - Handles zoom/pan and node drag for citation graph
 */

import type { NetworkNode, Transform } from "./types";
import type { GraphRenderer } from "./_GraphRenderer";

export interface InteractionState {
  transform: Transform;
  isDragging: boolean;
}

export function setupZoomPan(
  renderer: GraphRenderer,
  state: InteractionState,
): void {
  const svg = renderer.getSvg();
  if (!svg) return;

  let isPanning = false;
  let startX = 0;
  let startY = 0;

  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const rect = svg.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const newK = Math.max(0.1, Math.min(5, state.transform.k * scaleFactor));
    state.transform.x =
      mouseX - (mouseX - state.transform.x) * (newK / state.transform.k);
    state.transform.y =
      mouseY - (mouseY - state.transform.y) * (newK / state.transform.k);
    state.transform.k = newK;

    renderer.applyTransform(state.transform);
  });

  svg.addEventListener("mousedown", (e) => {
    if (e.target === svg || (e.target as Element).closest(".graph-edges")) {
      isPanning = true;
      startX = e.clientX - state.transform.x;
      startY = e.clientY - state.transform.y;
      svg.style.cursor = "grabbing";
    }
  });

  svg.addEventListener("mousemove", (e) => {
    if (isPanning && !state.isDragging) {
      state.transform.x = e.clientX - startX;
      state.transform.y = e.clientY - startY;
      renderer.applyTransform(state.transform);
    }
  });

  svg.addEventListener("mouseup", () => {
    isPanning = false;
    svg.style.cursor = "grab";
  });
  svg.addEventListener("mouseleave", () => {
    isPanning = false;
    svg.style.cursor = "grab";
  });
  svg.style.cursor = "grab";
}

export function startNodeDrag(
  e: MouseEvent,
  node: NetworkNode,
  renderer: GraphRenderer,
  state: InteractionState,
): void {
  e.stopPropagation();
  state.isDragging = true;

  const svg = renderer.getSvg()!;
  const rect = svg.getBoundingClientRect();

  const onMouseMove = (moveEvent: MouseEvent) => {
    const x =
      (moveEvent.clientX - rect.left - state.transform.x) / state.transform.k;
    const y =
      (moveEvent.clientY - rect.top - state.transform.y) / state.transform.k;
    node.fx = x;
    node.fy = y;
    node.x = x;
    node.y = y;
    renderer.getSimulation()?.reheat();
  };

  const onMouseUp = () => {
    state.isDragging = false;
    if (!node.is_seed) {
      node.fx = null;
      node.fy = null;
    }
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  };

  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
}
