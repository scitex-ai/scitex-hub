/** Render Sphinx diagrams after their theme scripts have been stripped. */
import { appendSvgImage } from "@/utils/diagram-svg";

const pending = new WeakSet<HTMLElement>();
let sequence = 0;

export async function renderSphinxDiagrams(container: HTMLElement): Promise<void> {
  const nodes = Array.from(container.querySelectorAll<HTMLElement>(
    ".sphinx-inline-content pre.mermaid, .sphinx-inline-content div.mermaid",
  )).filter((node) => !pending.has(node) && !node.dataset.docsDiagram);
  if (!nodes.length) return;
  nodes.forEach((node) => pending.add(node));
  try {
    const { default: mermaid } = await import("mermaid");
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      htmlLabels: false,
      theme: document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "default",
      flowchart: { htmlLabels: false },
    });
    for (const node of nodes) {
      if (!node.isConnected) continue;
      const source = node.textContent?.trim();
      if (!source) continue;
      try {
        const { svg } = await mermaid.render(`docs-diagram-${++sequence}`, source);
        if (!node.isConnected) continue;
        const wrapper = document.createElement("div");
        wrapper.className = "sphinx-diagram";
        appendSvgImage(wrapper, svg, "Documentation diagram");
        wrapper.dataset.docsDiagram = "rendered";
        node.replaceWith(wrapper);
      } catch {
        // Keep the readable source when an individual diagram is invalid.
        node.dataset.docsDiagram = "unavailable";
        node.setAttribute("aria-label", "Diagram source; preview unavailable");
      }
    }
  } catch {
    // The rest of the document remains usable if the optional chunk cannot load.
    nodes.forEach((node) => pending.delete(node));
  }
}
