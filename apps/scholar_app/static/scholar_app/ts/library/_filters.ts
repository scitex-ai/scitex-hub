/**
 * Filtering and sorting logic for Scholar Library
 */

import { LibraryPaper, LibraryStats } from "./types";

export class LibraryFilters {
  static calculateStats(papers: LibraryPaper[]): LibraryStats {
    const stats: LibraryStats = {
      total: papers.length,
      to_read: 0,
      reading: 0,
      read: 0,
      referenced: 0,
      favorite: 0,
    };

    papers.forEach((paper) => {
      if (paper.reading_status === "to_read") stats.to_read++;
      if (paper.reading_status === "reading") stats.reading++;
      if (paper.reading_status === "read") stats.read++;
      if (paper.reading_status === "referenced") stats.referenced++;
      if (paper.tags?.includes("favorite")) stats.favorite++;
    });

    return stats;
  }

  static applyFilters(
    papers: LibraryPaper[],
    statusFilter: string | null,
    searchQuery: string,
  ): LibraryPaper[] {
    return papers.filter((paper) => {
      // Status filter
      if (statusFilter === "favorite") {
        if (!paper.tags?.includes("favorite")) return false;
      } else if (statusFilter && statusFilter !== "all") {
        if (paper.reading_status !== statusFilter) return false;
      }

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const searchableText = [
          paper.title,
          paper.authors,
          paper.journal,
          paper.abstract,
          paper.doi,
          ...(paper.tags || []),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        if (!searchableText.includes(query)) return false;
      }

      return true;
    });
  }

  static sortPapers(papers: LibraryPaper[], sortBy: string): LibraryPaper[] {
    const sorted = [...papers];

    switch (sortBy) {
      case "date":
        sorted.sort(
          (a, b) =>
            new Date(b.saved_at).getTime() - new Date(a.saved_at).getTime(),
        );
        break;
      case "title":
        sorted.sort((a, b) => a.title.localeCompare(b.title));
        break;
      case "importance":
        sorted.sort((a, b) => b.importance_rating - a.importance_rating);
        break;
      case "year":
        sorted.sort((a, b) => (b.year || 0) - (a.year || 0));
        break;
      default:
        break;
    }

    return sorted;
  }
}
