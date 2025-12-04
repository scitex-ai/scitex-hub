/**
 * DiffMerge Merge Handler
 */

import { DiffMergeConfig, MergeResult } from "./types.ts";
import { getCSRFToken } from "./utils.ts";

export class MergeHandler {
  private config: DiffMergeConfig;

  constructor(config: DiffMergeConfig) {
    this.config = config;
  }

  /**
   * Merge contents
   */
  public async merge(
    leftContent: string,
    rightContent: string,
    strategy: "left" | "right" | "manual"
  ): Promise<void> {
    try {
      const formData = new FormData();
      formData.append("content_left", leftContent);
      formData.append("content_right", rightContent);
      formData.append("merge_strategy", strategy);

      const response = await fetch(
        `${this.config.apiBaseUrl}api/merge-contents/`,
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
        throw new Error(error.error || "Failed to merge");
      }

      const data: MergeResult = await response.json();
      this.renderMergeResult(data);
    } catch (error) {
      console.error("Error merging:", error);
      alert(`Error merging: ${error}`);
    }
  }

  /**
   * Render merge result
   */
  private renderMergeResult(result: MergeResult): void {
    const mergeResults = document.getElementById("merge-results");
    const mergedContent = document.getElementById("merged-content-display");

    if (!mergeResults || !mergedContent) return;

    mergedContent.textContent = result.merged_content;
    mergeResults.style.display = "block";

    const downloadBtn = document.getElementById("download-merged");
    if (downloadBtn) downloadBtn.style.display = "inline-flex";
  }

  /**
   * Download merged content
   */
  public downloadMerged(): void {
    const mergedContent = document.getElementById("merged-content-display");
    if (!mergedContent) return;

    const content = mergedContent.textContent || "";
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "merged.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  /**
   * Copy merged content
   */
  public async copyMerged(): Promise<void> {
    const mergedContent = document.getElementById("merged-content-display");
    if (!mergedContent) return;

    const content = mergedContent.textContent || "";
    try {
      await navigator.clipboard.writeText(content);
      alert("Copied to clipboard!");
    } catch (error) {
      console.error("Error copying to clipboard:", error);
      alert("Failed to copy to clipboard");
    }
  }
}
