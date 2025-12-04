/**
 * Table API Client
 * Handles API communication for table data
 */

console.log("[DEBUG] table-preview-modal/table-api.ts loaded");

import { getCsrfToken } from "../../shared/utils.js";
import { TableData } from "./types.js";

export class TableAPIClient {
  constructor(private projectId: string) {}

  async loadTableData(fileHash: string): Promise<TableData> {
    const apiUrl = `/writer/api/project/${this.projectId}/table-data/${fileHash}/`;
    console.log("[TableAPIClient] Fetching from:", apiUrl);

    const response = await fetch(apiUrl);
    const result = await response.json();

    if (result.success) {
      return result;
    } else {
      throw new Error(result.error || "Failed to load table data");
    }
  }

  async saveTableData(
    fileHash: string,
    data: Record<string, any>[],
    columns: string[],
  ): Promise<void> {
    const apiUrl = `/writer/api/project/${this.projectId}/table-update/${fileHash}/`;
    console.log("[TableAPIClient] Saving to:", apiUrl);

    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        data: data,
        columns: columns,
      }),
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || "Failed to save table");
    }

    console.log("[TableAPIClient] Save successful");
  }
}
