/**
 * DiffMerge Diff Renderer
 */

import { DiffMergeConfig, DiffResult } from "./types.ts";
import { getCSRFToken, escapeHtml } from "./utils.ts";

export class DiffRenderer {
  private config: DiffMergeConfig;
  private onDiffComputed: () => void;

  constructor(config: DiffMergeConfig, onDiffComputed: () => void) {
    this.config = config;
    this.onDiffComputed = onDiffComputed;
  }

  /**
   * Compute diff
   */
  public async computeDiff(
    leftContent: string,
    rightContent: string,
    leftFilename: string,
    rightFilename: string
  ): Promise<void> {
    if (!leftContent && !rightContent) {
      alert("Please provide content on both sides");
      return;
    }

    try {
      const formData = new FormData();
      formData.append("content_left", leftContent);
      formData.append("content_right", rightContent);
      formData.append("filename_left", leftFilename);
      formData.append("filename_right", rightFilename);

      const response = await fetch(
        `${this.config.apiBaseUrl}api/compute-diff/`,
        {
          method: "POST",
          headers: {
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: formData,
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to compute diff");
      }

      const data: DiffResult = await response.json();
      this.renderDiff(data);
      this.onDiffComputed();
    } catch (error) {
      console.error("Error computing diff:", error);
      alert(`Error computing diff: ${error}`);
    }
  }

  /**
   * Render diff
   */
  private renderDiff(result: DiffResult): void {
    const diffResults = document.getElementById("diff-results");
    const tableBody = document.getElementById("diff-table-body");
    const statsAdditions = document.getElementById("stats-additions");
    const statsDeletions = document.getElementById("stats-deletions");

    if (!diffResults || !tableBody) return;

    // Update statistics
    if (statsAdditions) {
      statsAdditions.textContent = `+${result.statistics.additions} addition${
        result.statistics.additions !== 1 ? "s" : ""
      }`;
    }
    if (statsDeletions) {
      statsDeletions.textContent = `-${result.statistics.deletions} deletion${
        result.statistics.deletions !== 1 ? "s" : ""
      }`;
    }

    // Render diff lines
    tableBody.innerHTML = "";
    result.diff_lines.forEach((line) => {
      if (line.type !== "header") {
        const row = document.createElement("tr");
        row.className = `diff-line ${line.type}`;
        row.innerHTML = `
          <td class="diff-line-num"></td>
          <td class="diff-line-num"></td>
          <td class="diff-line-content">${escapeHtml(line.content)}</td>
        `;
        tableBody.appendChild(row);
      }
    });

    diffResults.style.display = "block";
  }

  /**
   * Show merge buttons
   */
  public showMergeButtons(): void {
    const mergeLeft = document.getElementById("merge-left");
    const mergeRight = document.getElementById("merge-right");
    const mergeManual = document.getElementById("merge-manual");

    if (mergeLeft) mergeLeft.style.display = "inline-flex";
    if (mergeRight) mergeRight.style.display = "inline-flex";
    if (mergeManual) mergeManual.style.display = "inline-flex";
  }
}
