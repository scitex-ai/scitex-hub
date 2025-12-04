/**
 * Citation Sorting Module
 * Handles sorting of citations by various criteria
 */

import { Citation } from "./types.js";

export class CitationSorting {
  /**
   * Sort citations by specified criteria
   */
  public sortCitations(citations: Citation[], sortBy: string): Citation[] {
    const sorted = [...citations];

    switch (sortBy) {
      case "citation-count":
        sorted.sort((a, b) => (b.citation_count || 0) - (a.citation_count || 0));
        break;
      case "year-desc":
        sorted.sort((a, b) => (b.year || "0").localeCompare(a.year || "0"));
        break;
      case "year-asc":
        sorted.sort((a, b) => (a.year || "0").localeCompare(b.year || "0"));
        break;
      case "alpha":
        sorted.sort((a, b) => a.key.localeCompare(b.key));
        break;
      default:
        console.warn(`[CitationSorting] Unknown sort type: ${sortBy}`);
    }

    console.log(`[CitationSorting] Sorted ${sorted.length} citations by ${sortBy}`);
    return sorted;
  }
}
