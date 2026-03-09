/**
 * StatsCalculator - Main orchestrator for statistics calculator
 */

import { DataTableManager } from "@/components/data-table/index.ts";
import type { Dataset } from "@/components/data-table/types.ts";
import { StatsApiClient } from "./_api-client";
import { FlowchartPanel } from "./_flowchart-panel";
import { ResultsRenderer } from "./_results-renderer";
import { TEST_REGISTRY, WORKFLOW_CATEGORIES } from "./_test-registry";
import type { StatsTestConfig, WorkflowCategory } from "./types";

export class StatsCalculator {
  private dataTable: DataTableManager;
  private apiClient: StatsApiClient;
  private renderer: ResultsRenderer;
  private flowchart: FlowchartPanel | null = null;
  private currentTest = "descriptive";

  constructor() {
    this.apiClient = new StatsApiClient();
    this.renderer = new ResultsRenderer("#resultsContent");

    // Initialize DataTable with config object
    this.dataTable = new DataTableManager({
      container: "#stats-data-table",
      onDataChange: () => this.onDataChanged(),
      onStatusUpdate: (msg: string) => this.updateStatus(msg),
    });

    this.initUI();
    this.initDataTable();
    this.initFlowchart();
  }

  private initUI(): void {
    this.renderTestPanel();
    this.setupCalculateButton();
    this.setupRecommendButton();
    this.setupDataPanelToggle();
  }

  private initFlowchart(): void {
    const container = document.getElementById("flowchartContainer");
    if (!container) return;
    this.flowchart = new FlowchartPanel(
      "#flowchartContainer",
      (testId: string) => this.selectTestById(testId),
    );
    this.flowchart.load();
  }

  /** Select a test by its registry ID (used by flowchart click) */
  selectTestById(testId: string): void {
    const btn = document.querySelector<HTMLElement>(
      `.test-btn[data-test="${testId}"]`,
    );
    if (btn) {
      this.selectTest(btn);
      // Scroll button into view in the test panel
      btn.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  private initDataTable(): void {
    const initialData: Dataset = {
      columns: ["Group A", "Group B", "Group C"],
      rows: Array.from({ length: 20 }, () => ({
        "Group A": "",
        "Group B": "",
        "Group C": "",
      })),
    };
    this.dataTable.setCurrentData(initialData);
    this.dataTable.renderEditableDataTable();
    this.dataTable.setupColumnResizing();
  }

  private renderTestPanel(): void {
    const panel = document.getElementById("testSelectionPanel");
    if (!panel) return;

    let html = "";
    for (const [catId, catInfo] of Object.entries(WORKFLOW_CATEGORIES)) {
      const tests = Object.values(TEST_REGISTRY).filter(
        (t) => t.category === catId,
      );
      html += `
        <div class="test-category">
          <button class="category-label" data-category="${catId}">
            <span>${catInfo.label}</span>
            <span class="category-count">${tests.length}</span>
            <i class="fas fa-chevron-right category-chevron"></i>
          </button>
          <div class="test-selector expanded">
            ${this.renderTestButtons(tests)}
          </div>
        </div>
      `;
    }
    panel.innerHTML = html;

    // Accordion toggle for category headers
    panel.querySelectorAll(".category-label").forEach((header) => {
      header.addEventListener("click", () => {
        const items = header.nextElementSibling as HTMLElement;
        if (!items) return;
        const isExpanded = items.classList.contains("expanded");
        header.classList.toggle("expanded", !isExpanded);
        items.classList.toggle("expanded", !isExpanded);
      });
      // Start expanded
      header.classList.add("expanded");
    });

    panel.querySelectorAll(".test-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.selectTest(btn as HTMLElement));
    });
  }

  /** Render test buttons, grouping by subCategory if present */
  private renderTestButtons(tests: StatsTestConfig[]): string {
    const hasSubCategories = tests.some((t) => t.subCategory);
    if (!hasSubCategories) {
      return tests.map((t) => this.renderOneTestBtn(t)).join("");
    }
    // Group by subCategory preserving order
    const groups: { label: string; items: StatsTestConfig[] }[] = [];
    for (const t of tests) {
      const label = t.subCategory || "";
      const last = groups[groups.length - 1];
      if (last && last.label === label) {
        last.items.push(t);
      } else {
        groups.push({ label, items: [t] });
      }
    }
    return groups
      .map(
        (g) =>
          `<div class="test-sub-group">
            <span class="sub-group-label">${g.label}</span>
            <div class="sub-group-items">${g.items.map((t) => this.renderOneTestBtn(t)).join("")}</div>
          </div>`,
      )
      .join("");
  }

  private renderOneTestBtn(t: StatsTestConfig): string {
    return `<button class="test-btn${t.id === this.currentTest ? " active" : ""}"
                    data-test="${t.id}" data-mode="${t.dataMode}"
                    title="${t.description}">
              <span class="test-name">${t.name}</span>
              <span class="test-description">${t.description}</span>
            </button>`;
  }

  private selectTest(btn: HTMLElement): void {
    const testId = btn.dataset.test;
    if (!testId) return;

    document
      .querySelectorAll(".test-btn")
      .forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    this.currentTest = testId;

    // Update data table columns based on test's dataParams
    this.updateColumns(testId);

    // Sync flowchart highlight
    if (this.flowchart) {
      this.flowchart.highlightByTestId(testId);
    }

    this.updateStatus(`Selected test: ${TEST_REGISTRY[testId].name}`);
  }

  private updateColumns(testId: string): void {
    const config = TEST_REGISTRY[testId];
    if (!config.dataParams || config.dataParams.length === 0) return;

    const columns = config.dataParams;
    const rows: Record<string, string>[] = Array.from({ length: 20 }, () => {
      const row: Record<string, string> = {};
      columns.forEach((col) => {
        row[col] = "";
      });
      return row;
    });

    this.dataTable.setCurrentData({ columns, rows });
    this.dataTable.renderEditableDataTable();
    this.dataTable.setupColumnResizing();
  }

  /** Data panel toggle (not managed by resizer since it's flex:1) */
  private setupDataPanelToggle(): void {
    const btn = document.getElementById("data-panel-toggle");
    const panel = document.querySelector(".stats-data-panel") as HTMLElement;
    if (!btn || !panel) return;

    const STORAGE_KEY = "scitex-stats-data-collapsed";
    const icon = btn.querySelector("i");

    // Restore state
    if (localStorage.getItem(STORAGE_KEY) === "true") {
      panel.classList.add("collapsed");
      if (icon) {
        icon.classList.replace("fa-chevron-left", "fa-chevron-right");
      }
    }

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isCollapsed = panel.classList.toggle("collapsed");
      if (isCollapsed) {
        panel.style.width = "";
        panel.style.flex = "";
        panel.style.minWidth = "";
      } else {
        panel.style.flex = "1";
        panel.style.minWidth = "200px";
      }
      if (icon) {
        icon.classList.replace(
          isCollapsed ? "fa-chevron-left" : "fa-chevron-right",
          isCollapsed ? "fa-chevron-right" : "fa-chevron-left",
        );
      }
      localStorage.setItem(STORAGE_KEY, String(isCollapsed));
    });
  }

  private setupCalculateButton(): void {
    const btn = document.getElementById("calculateBtn");
    if (!btn) return;

    btn.addEventListener("click", () => this.calculate());
  }

  private setupRecommendButton(): void {
    const btn = document.getElementById("recommendBtn");
    if (!btn) return;

    btn.addEventListener("click", () => this.handleRecommend());
  }

  private async calculate(): Promise<void> {
    const config = TEST_REGISTRY[this.currentTest];
    if (!config) {
      this.renderer.renderError("Test not found.");
      return;
    }

    this.updateStatus("Calculating...");

    const extractedData = this.extractData();
    if (!extractedData) {
      this.renderer.renderError(
        "Failed to extract data. Check your table input.",
      );
      return;
    }

    let result;
    try {
      switch (config.endpoint) {
        case "describe":
          result = await this.apiClient.describe(extractedData.single || []);
          if (result.success) {
            this.showBackendIndicator();
            this.renderer.renderDescriptive(result.result);
          } else {
            this.renderer.renderError(result.error || "Failed to calculate.");
          }
          break;

        case "calculate": {
          const { single, paired, groups } = extractedData;
          result = await this.apiClient.calculate(
            config.testName || "",
            single,
            paired?.[1],
            groups,
            "two-sided",
            true,
          );
          if (result.success) {
            this.showBackendIndicator();
            this.renderer.renderTestResult(result, config);
          } else {
            this.renderer.renderError(result.error || "Failed to calculate.");
          }
          break;
        }

        case "effect-size":
          if (config.measure && extractedData.paired) {
            result = await this.apiClient.effectSize(
              config.measure,
              extractedData.paired[0],
              extractedData.paired[1],
            );
            if (result.success) {
              this.showBackendIndicator();
              this.renderer.renderEffectSize(result.result);
            } else {
              this.renderer.renderError(
                result.error || "Failed to calculate effect size.",
              );
            }
          } else {
            this.renderer.renderError("Effect size requires two groups.");
          }
          break;

        case "posthoc":
          if (config.method && extractedData.groups) {
            const dataset = this.dataTable.getCurrentData();
            const groupNames = dataset?.columns || undefined;
            result = await this.apiClient.posthoc(
              config.method,
              extractedData.groups,
              groupNames,
            );
            if (result.success) {
              this.showBackendIndicator();
              this.renderer.renderPosthoc(result.result);
            } else {
              this.renderer.renderError(
                result.error || "Failed to run post-hoc test.",
              );
            }
          } else {
            this.renderer.renderError("Post-hoc requires multiple groups.");
          }
          break;

        case "power":
          // Power analysis requires parameter inputs, not raw data
          this.renderer.renderError(
            "Power analysis not yet implemented via data table. Use parameters.",
          );
          break;

        case "correct":
          if (extractedData.pvalues) {
            result = await this.apiClient.correct(
              config.method || "fdr_bh",
              extractedData.pvalues,
            );
            if (result.success) {
              this.showBackendIndicator();
              this.renderer.renderCorrection(result.result);
            } else {
              this.renderer.renderError(
                result.error || "Failed to correct p-values.",
              );
            }
          } else {
            this.renderer.renderError(
              "Correction requires p-values in the first column.",
            );
          }
          break;

        default:
          this.renderer.renderError("Unknown endpoint.");
      }
    } catch (error) {
      this.renderer.renderError(
        error instanceof Error ? error.message : "Unexpected error.",
      );
    }

    this.updateStatus("Calculation complete.");
  }

  private extractData(): Record<string, any> | null {
    const dataset = this.dataTable.getCurrentData();
    if (!dataset || !dataset.columns || dataset.columns.length === 0) {
      return null;
    }

    const config = TEST_REGISTRY[this.currentTest];
    const mode = config.dataMode;

    const columnData: number[][] = dataset.columns.map((col) => {
      return dataset.rows
        .map((row) => row[col])
        .filter((v) => v !== "" && v !== null && v !== undefined)
        .map((v) => parseFloat(String(v)))
        .filter((v) => !isNaN(v));
    });

    switch (mode) {
      case "single":
        return { single: columnData[0] || [] };

      case "paired":
        return {
          paired: [columnData[0] || [], columnData[1] || []],
          single: columnData[0] || [],
        };

      case "groups":
        return { groups: columnData.filter((g) => g.length > 0) };

      case "pvalues":
        return { pvalues: columnData[0] || [] };

      case "params":
        return { params: {} }; // For now, params require manual input

      default:
        return null;
    }
  }

  private async handleRecommend(): Promise<void> {
    this.updateStatus("Getting recommendations...");

    // Simple recommendation based on current data structure
    const dataset = this.dataTable.getCurrentData();
    if (!dataset || !dataset.columns || dataset.columns.length === 0) {
      this.renderer.renderError("No data available for recommendation.");
      return;
    }

    const nGroups = dataset.columns.length;
    const result = await this.apiClient.recommend({
      n_groups: nGroups,
      outcome_type: "continuous",
      design: "between",
      top_k: 3,
    });

    if (result.success && result.result.recommendations) {
      this.renderer.renderRecommendations(result.result.recommendations);
    } else {
      this.renderer.renderError(
        result.error || "Failed to get recommendations.",
      );
    }

    this.updateStatus("Recommendations ready.");
  }

  private onDataChanged(): void {
    // Data changed in the table - could add auto-calculate or status hints
  }

  private showBackendIndicator(): void {
    const indicator = document.getElementById("backendIndicator");
    if (indicator) {
      indicator.innerHTML =
        '<span class="backend-indicator backend-scitex">SCITEX BACKEND</span>';
    }
  }

  private updateStatus(message: string): void {
    console.log("[StatsCalculator]", message);
  }
}
