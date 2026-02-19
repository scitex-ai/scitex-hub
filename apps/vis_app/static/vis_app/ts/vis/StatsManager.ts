/**
 * StatsManager - Statistical Testing Integration for SciTeX Vis
 *
 * "Magic" statistical testing: when users draw plots, statistical tests
 * automatically run and significance markers (stars) appear.
 *
 * Features:
 * - Right-click menu shows only applicable tests with tooltips
 * - Run recommended test automatically
 * - Run all applicable tests in parallel
 * - Display results in Stats Inspector panel
 * - Render brackets and stars on canvas
 */

import { fabric } from "fabric";
import type {
  StatContext,
  TestMenuItem,
  SummaryStats,
  EffectSize,
  TestResult,
  StatAnnotation,
  GroupData,
} from "./StatsTypes.ts";
import {
  getApplicableTests,
  runTest,
  runAllApplicable,
  buildContextFromPlot,
} from "./StatsApiClient.ts";

// Re-export all types from StatsTypes for backward compatibility
export type {
  StatContext,
  TestMenuItem,
  SummaryStats,
  EffectSize,
  TestResult,
  StatAnnotation,
  GroupData,
} from "./StatsTypes.ts";

export class StatsManager {
  private canvas: fabric.Canvas | null = null;
  private statsInspector: HTMLElement | null = null;
  private contextMenu: HTMLElement | null = null;

  constructor() {
    this.createContextMenu();
    this.createStatsInspector();
  }

  /**
   * Set the Fabric.js canvas reference
   */
  public setCanvas(canvas: fabric.Canvas): void {
    this.canvas = canvas;
  }

  // =========================================================================
  // API Calls - delegated to StatsApiClient
  // =========================================================================

  /**
   * Get applicable tests for the given context
   */
  public async getApplicableTests(context: StatContext): Promise<{
    items: TestMenuItem[];
    recommended: string[];
    effect_sizes: string[];
    posthoc: string[];
  }> {
    return getApplicableTests(context);
  }

  /**
   * Run a specific statistical test
   */
  public async runTest(
    testName: string,
    groups: GroupData[],
    options: {
      paired?: boolean;
      correction_method?: string;
    } = {},
  ): Promise<{ result: TestResult; annotation: StatAnnotation }> {
    return runTest(testName, groups, options);
  }

  /**
   * Run all applicable tests (magic mode)
   */
  public async runAllApplicable(
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
    return runAllApplicable(groups, options);
  }

  /**
   * Build StatContext from plot data
   */
  public async buildContextFromPlot(
    plotType: string,
    groups: GroupData[],
    metadata: Partial<StatContext> = {},
  ): Promise<{
    context: StatContext;
    applicable_tests: TestMenuItem[];
    recommended: string[];
    summary: SummaryStats[];
  }> {
    return buildContextFromPlot(plotType, groups, metadata);
  }

  // =========================================================================
  // Context Menu
  // =========================================================================

  private createContextMenu(): void {
    this.contextMenu = document.createElement("div");
    this.contextMenu.className = "stats-context-menu";
    this.contextMenu.style.cssText = `
            position: fixed;
            display: none;
            background: var(--color-canvas-default, #ffffff);
            border: 1px solid var(--color-border-default, #d0d7de);
            border-radius: 6px;
            box-shadow: 0 8px 24px rgba(140, 149, 159, 0.2);
            min-width: 200px;
            max-width: 300px;
            max-height: 400px;
            overflow-y: auto;
            z-index: 10000;
            font-size: 13px;
        `;
    document.body.appendChild(this.contextMenu);

    // Close on click outside
    document.addEventListener("click", () => this.hideContextMenu());
  }

  /**
   * Show context menu for statistical tests
   */
  public async showContextMenu(
    x: number,
    y: number,
    groups: GroupData[],
    onSelect: (testName: string) => void,
  ): Promise<void> {
    if (!this.contextMenu) return;

    try {
      // Build context and get applicable tests
      const { applicable_tests, recommended } = await buildContextFromPlot(
        "boxplot",
        groups,
      );

      // Build menu HTML
      let html = '<div class="stats-menu-header">Statistics</div>';

      // Recommended section
      if (recommended.length > 0) {
        html += '<div class="stats-menu-section">Recommended</div>';
        for (const testId of recommended) {
          const item = applicable_tests.find((t) => t.id === testId);
          if (item && item.enabled) {
            html += this.renderMenuItem(item, true);
          }
        }
        html += '<div class="stats-menu-divider"></div>';
      }

      // All tests by family
      const families = ["parametric", "nonparametric", "categorical"];
      for (const family of families) {
        const familyItems = applicable_tests.filter(
          (t) => t.family === family && !recommended.includes(t.id),
        );
        if (familyItems.length > 0) {
          const familyLabel = family.charAt(0).toUpperCase() + family.slice(1);
          html += `<div class="stats-menu-section">${familyLabel}</div>`;
          for (const item of familyItems) {
            html += this.renderMenuItem(item, false);
          }
        }
      }

      this.contextMenu.innerHTML = html;

      // Add click handlers
      this.contextMenu
        .querySelectorAll(".stats-menu-item:not(.disabled)")
        .forEach((el) => {
          el.addEventListener("click", (e) => {
            e.stopPropagation();
            const testId = (el as HTMLElement).dataset.testId;
            if (testId) {
              onSelect(testId);
              this.hideContextMenu();
            }
          });
        });

      // Position and show
      this.contextMenu.style.left = `${x}px`;
      this.contextMenu.style.top = `${y}px`;
      this.contextMenu.style.display = "block";

      // Adjust if off-screen
      const rect = this.contextMenu.getBoundingClientRect();
      if (rect.right > window.innerWidth) {
        this.contextMenu.style.left = `${window.innerWidth - rect.width - 10}px`;
      }
      if (rect.bottom > window.innerHeight) {
        this.contextMenu.style.top = `${window.innerHeight - rect.height - 10}px`;
      }
    } catch (error) {
      console.error("Failed to show stats context menu:", error);
    }
  }

  private renderMenuItem(item: TestMenuItem, isRecommended: boolean): string {
    const classes = ["stats-menu-item"];
    if (!item.enabled) classes.push("disabled");
    if (isRecommended) classes.push("recommended");

    const tooltip = item.tooltip ? `title="${item.tooltip}"` : "";
    const badge = isRecommended
      ? '<span class="recommended-badge">Recommended</span>'
      : "";

    return `
            <div class="${classes.join(" ")}" data-test-id="${item.id}" ${tooltip}>
                <span class="menu-label">${item.label}</span>
                ${badge}
            </div>
        `;
  }

  public hideContextMenu(): void {
    if (this.contextMenu) {
      this.contextMenu.style.display = "none";
    }
  }

  // =========================================================================
  // Stats Inspector Panel
  // =========================================================================

  private createStatsInspector(): void {
    // Will be initialized when panel is first opened
  }

  /**
   * Show stats inspector with results
   */
  public showStatsInspector(data: { tests: any[]; effects: any[] }): void {
    let panel = document.getElementById("stats-inspector-panel");

    if (!panel) {
      panel = document.createElement("div");
      panel.id = "stats-inspector-panel";
      panel.className = "stats-inspector-panel";
      document.body.appendChild(panel);
    }

    // Render content
    panel.innerHTML = `
            <div class="stats-inspector-header">
                <span>Statistics Inspector</span>
                <button class="close-btn" onclick="this.parentElement.parentElement.style.display='none'">x</button>
            </div>
            <div class="stats-inspector-content">
                <h4>Tests</h4>
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th>Test</th>
                            <th>p-value</th>
                            <th>Effect</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.tests
                          .map(
                            (t) => `
                            <tr>
                                <td>${t.label || t.name}</td>
                                <td>${this.formatPValue(t.p_adj || t.p_raw)}</td>
                                <td>${t.stat?.toFixed(3) || "-"}</td>
                            </tr>
                        `,
                          )
                          .join("")}
                    </tbody>
                </table>

                ${
                  data.effects.length > 0
                    ? `
                    <h4>Effect Sizes</h4>
                    <table class="stats-table">
                        <thead>
                            <tr>
                                <th>Measure</th>
                                <th>Value</th>
                                <th>Interpretation</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.effects
                              .map(
                                (e) => `
                                <tr>
                                    <td>${e.label || e.name}</td>
                                    <td>${e.value?.toFixed(3) || "-"}</td>
                                    <td>${e.note || "-"}</td>
                                </tr>
                            `,
                              )
                              .join("")}
                        </tbody>
                    </table>
                `
                    : ""
                }
            </div>
        `;

    panel.style.display = "block";
  }

  private formatPValue(p: number | null): string {
    if (p === null) return "-";
    if (p < 0.001) return "< 0.001 ***";
    if (p < 0.01) return `${p.toFixed(3)} **`;
    if (p < 0.05) return `${p.toFixed(3)} *`;
    return `${p.toFixed(3)} ns`;
  }

  // =========================================================================
  // Canvas Annotations (Brackets & Stars)
  // =========================================================================

  /**
   * Add a statistical bracket annotation to the canvas
   */
  public addStatBracket(
    annotation: StatAnnotation,
    positions: { x1: number; y1: number; x2: number; y2: number },
  ): fabric.Group | null {
    if (!this.canvas) return null;

    const { x1, y1, x2, y2 } = positions;
    const bracketHeight = annotation.bracket_style.bracket_height;
    const starOffset = annotation.bracket_style.star_offset;

    // Calculate bracket position (above the higher point)
    const topY = Math.min(y1, y2) - 20;

    // Create bracket lines
    const leftLine = new fabric.Line([x1, topY + bracketHeight, x1, topY], {
      stroke: "#000000",
      strokeWidth: 1,
    });

    const rightLine = new fabric.Line([x2, topY + bracketHeight, x2, topY], {
      stroke: "#000000",
      strokeWidth: 1,
    });

    const topLine = new fabric.Line([x1, topY, x2, topY], {
      stroke: "#000000",
      strokeWidth: 1,
    });

    // Create stars text
    const starsText = new fabric.Text(annotation.stars || "ns", {
      left: (x1 + x2) / 2,
      top: topY - starOffset - 10,
      fontSize: 14,
      fontFamily: "Arial",
      originX: "center",
      fill: "#000000",
    });

    // Group all elements
    const group = new fabric.Group([leftLine, rightLine, topLine, starsText], {
      selectable: true,
      hasControls: true,
      lockRotation: true,
    });

    // Store annotation data
    (group as any).statAnnotation = annotation;

    this.canvas.add(group);
    this.canvas.renderAll();

    return group;
  }

  /**
   * Extract group data from selected canvas objects (e.g., boxplots)
   */
  public extractGroupsFromSelection(): GroupData[] {
    if (!this.canvas) return [];

    const activeObjects = this.canvas.getActiveObjects();
    const groups: GroupData[] = [];

    for (const obj of activeObjects) {
      // Check if object has plot data
      const plotData = (obj as any).plotData;
      if (plotData && plotData.values) {
        groups.push({
          name: plotData.label || `Group ${groups.length + 1}`,
          values: plotData.values,
        });
      }
    }

    return groups;
  }
}

// Singleton instance
export const statsManager = new StatsManager();
