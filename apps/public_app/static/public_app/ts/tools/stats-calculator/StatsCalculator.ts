/**
 * StatsCalculator - Main orchestrator for statistics calculator
 */

import { DataTableManager } from "@/components/data-table/index.ts";
import type { Dataset } from "@/components/data-table/types.ts";
import { StatsApiClient } from "./api-client.ts";
import { ResultsRenderer } from "./results-renderer.ts";
import { TEST_REGISTRY, WORKFLOW_CATEGORIES } from "./test-registry.ts";
import type { StatsTestConfig, WorkflowCategory } from "./types.ts";

export class StatsCalculator {
  private dataTable: DataTableManager;
  private apiClient: StatsApiClient;
  private renderer: ResultsRenderer;
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
  }

  private initUI(): void {
    this.renderTestPanel();
    this.setupCalculateButton();
    this.setupRecommendButton();
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
          <div class="category-label">${catInfo.label}</div>
          <div class="category-description">${catInfo.description}</div>
          <div class="test-selector">
            ${tests
              .map(
                (t) => `
              <button class="test-btn${t.id === this.currentTest ? " active" : ""}"
                      data-test="${t.id}"
                      data-mode="${t.dataMode}"
                      title="${t.description}">
                <span class="test-name">${t.name}</span>
                <span class="test-description">${t.description}</span>
              </button>
            `,
              )
              .join("")}
          </div>
        </div>
      `;
    }
    panel.innerHTML = html;

    panel.querySelectorAll(".test-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.selectTest(btn as HTMLElement));
    });
  }

  private selectTest(btn: HTMLElement): void {
    const testId = btn.dataset.test;
    if (!testId) return;

    document
      .querySelectorAll(".test-btn")
      .forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    this.currentTest = testId;

    this.updateStatus(`Selected test: ${TEST_REGISTRY[testId].name}`);
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
          );
          if (result.success) {
            this.showBackendIndicator();
            this.renderer.renderTestResult(result.result, config);
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
