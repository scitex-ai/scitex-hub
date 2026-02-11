/**
 * FlowchartPanel - Interactive statistical test decision flowchart
 *
 * Fetches Mermaid markup from /api/stats/flowchart/ and renders it
 * client-side using Mermaid.js. Attaches click handlers to let users
 * navigate "Which test should I use?" decisions.
 */

import mermaid from "mermaid";

// Mapping from SVG node IDs to test registry IDs
// SVG node IDs follow pattern: flowchart-{node_id}-{index}
const NODE_TEST_MAP: Record<string, string> = {
  shapiro: "shapiro",
  ttest_ind: "ttest_ind",
  indep_2_nonparam: "brunnermunzel",
  indep_2_alt: "mannwhitney",
  ttest_paired: "ttest_paired",
  wilcoxon: "wilcoxon",
  anova: "anova",
  kruskal: "kruskal",
  tukey: "tukey",
  games_howell: "games_howell",
  dunnett: "dunnett",
  cat_indep: "chi2",
  pearson: "pearson",
  spearman: "spearman",
};

export class FlowchartPanel {
  private container: HTMLElement;
  private onTestSelected: (testId: string) => void;
  private activeNodeId: string | null = null;

  constructor(selector: string, onTestSelected: (testId: string) => void) {
    const el = document.querySelector<HTMLElement>(selector);
    if (!el) throw new Error(`FlowchartPanel: ${selector} not found`);
    this.container = el;
    this.onTestSelected = onTestSelected;
  }

  async load(): Promise<void> {
    try {
      const resp = await fetch("/api/stats/flowchart/");
      if (!resp.ok) {
        this.container.innerHTML =
          '<div class="flowchart-error">Failed to load flowchart</div>';
        return;
      }
      const mermaidText = await resp.text();
      await this.renderMermaid(mermaidText);
      this.styleSvg();
      this.attachClickHandlers();
    } catch (err) {
      console.error("[FlowchartPanel] Load error:", err);
      this.container.innerHTML =
        '<div class="flowchart-error">Flowchart unavailable</div>';
    }
  }

  private async renderMermaid(text: string): Promise<void> {
    // Strip figrecipe's %%{init}%% directive — we configure Mermaid ourselves
    const cleaned = text.replace(/^%%\{.*?\}%%\s*/s, "");

    mermaid.initialize({
      startOnLoad: false,
      theme: "base",
      themeVariables: {
        primaryColor: "#e6f3ff",
        primaryTextColor: "#222",
        primaryBorderColor: "#0066cc",
        lineColor: "#888",
        fontSize: "14px",
        fontFamily: '"JetBrains Mono", "Courier New", monospace',
      },
      flowchart: {
        curve: "basis",
        padding: 16,
        nodeSpacing: 30,
        rankSpacing: 40,
        htmlLabels: true,
      },
      securityLevel: "loose",
    });

    const { svg } = await mermaid.render("stats-flowchart", cleaned);
    this.container.innerHTML = svg;
  }

  private styleSvg(): void {
    const svg = this.container.querySelector("svg");
    if (!svg) return;
    // Let CSS min-width control size; container scrolls
    svg.removeAttribute("height");
    svg.removeAttribute("width");
    svg.style.height = "auto";
    svg.style.display = "block";
  }

  private attachClickHandlers(): void {
    // Mermaid SVG nodes have id="flowchart-{nodeId}-{index}"
    const allElements = this.container.querySelectorAll("[id^='flowchart-']");

    allElements.forEach((el) => {
      const match = el.id.match(/^flowchart-(.+)-\d+$/);
      if (!match) return;

      const nodeId = match[1];
      const htmlEl = el as HTMLElement;
      htmlEl.style.cursor = "pointer";

      // Add hover class for CSS targeting
      htmlEl.classList.add("flowchart-node");
      if (nodeId in NODE_TEST_MAP) {
        htmlEl.classList.add("flowchart-leaf");
      }

      htmlEl.addEventListener("click", (e) => {
        e.stopPropagation();
        this.handleNodeClick(nodeId);
      });
    });
  }

  private handleNodeClick(nodeId: string): void {
    const testId = NODE_TEST_MAP[nodeId];
    if (testId) {
      this.highlightNode(nodeId);
      this.onTestSelected(testId);
    }
  }

  highlightNode(nodeId: string): void {
    // Remove previous highlight
    if (this.activeNodeId) {
      const prev = this.findSvgNode(this.activeNodeId);
      if (prev) prev.classList.remove("flowchart-active");
    }

    // Add new highlight
    const node = this.findSvgNode(nodeId);
    if (node) {
      node.classList.add("flowchart-active");
      this.activeNodeId = nodeId;
    }
  }

  /** Find the SVG node element by extracting from the flowchart-{id}-{N} pattern */
  private findSvgNode(nodeId: string): HTMLElement | null {
    const allNodes = this.container.querySelectorAll("[id^='flowchart-']");
    for (const el of allNodes) {
      const match = el.id.match(/^flowchart-(.+)-\d+$/);
      if (match && match[1] === nodeId) {
        return el as HTMLElement;
      }
    }
    return null;
  }

  /** Reverse lookup: find node ID from test registry ID */
  highlightByTestId(testId: string): void {
    for (const [nodeId, tid] of Object.entries(NODE_TEST_MAP)) {
      if (tid === testId) {
        this.highlightNode(nodeId);
        return;
      }
    }
  }
}
