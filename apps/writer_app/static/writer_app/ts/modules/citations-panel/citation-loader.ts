/**
 * Citation Loader Module
 * Handles loading citations from API
 */

import { Citation } from "./types.js";

export interface CitationsLoadResult {
  success: boolean;
  citations: Citation[];
}

export class CitationLoader {
  private projectId: string | null = null;

  constructor(projectId: string | null) {
    this.projectId = projectId;
  }

  /**
   * Load citations from API
   */
  public async loadCitations(): Promise<CitationsLoadResult> {
    if (!this.projectId) {
      console.error("[CitationLoader] No project ID available");
      return { success: false, citations: [] };
    }

    try {
      const apiUrl = `/writer/api/project/${this.projectId}/citations/`;
      console.log("[CitationLoader] Fetching from:", apiUrl);

      const response = await fetch(apiUrl);
      const data = await response.json();

      if (data.success && data.citations) {
        console.log(
          `[CitationLoader] Loaded ${data.citations.length} citations`,
        );
        return { success: true, citations: data.citations };
      } else {
        console.warn("[CitationLoader] No citations found");
        return { success: false, citations: [] };
      }
    } catch (error) {
      console.error("[CitationLoader] Error loading citations:", error);
      return { success: false, citations: [] };
    }
  }
}
