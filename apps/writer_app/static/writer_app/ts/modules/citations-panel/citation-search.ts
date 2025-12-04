/**
 * Citation Search Module
 * Handles search and filtering of citations
 */

import { Citation, CitationWithScore } from "./types.js";

export class CitationSearch {
  /**
   * Filter citations based on search query
   */
  public filterCitations(citations: Citation[], query: string): Citation[] {
    if (!query) {
      return [...citations];
    }

    const lowerQuery = query.trim().toLowerCase();
    const searchTerms = lowerQuery.split(/\s+/).filter((t) => t.length > 0);

    const withScores = citations
      .filter((cite) => this.matchesAllTerms(cite, searchTerms))
      .map((cite) => ({
        citation: cite,
        score: this.calculateRelevanceScore(cite, searchTerms),
      }))
      .sort((a, b) => b.score - a.score);

    return withScores.map((item) => item.citation);
  }

  /**
   * Check if citation matches all search terms
   */
  private matchesAllTerms(citation: Citation, searchTerms: string[]): boolean {
    const searchableText = this.buildSearchableText(citation);
    return searchTerms.every((term) => searchableText.includes(term));
  }

  /**
   * Build searchable text from citation fields
   */
  private buildSearchableText(citation: Citation): string {
    return [
      citation.key,
      citation.title || "",
      citation.journal || "",
      citation.year || "",
      ...(citation.authors || []),
      citation.abstract || "",
    ]
      .join(" ")
      .toLowerCase();
  }

  /**
   * Calculate relevance score for search results
   */
  private calculateRelevanceScore(
    citation: Citation,
    searchTerms: string[],
  ): number {
    let score = 0;

    searchTerms.forEach((term) => {
      score += this.scoreKeyMatch(citation.key, term);
      score += this.scoreTitleMatch(citation.title, term);
      score += this.scoreAuthorsMatch(citation.authors, term);
      score += this.scoreJournalMatch(citation.journal, term);
      score += this.scoreYearMatch(citation.year, term);
      score += this.scoreAbstractMatch(citation.abstract, term);
    });

    return score;
  }

  private scoreKeyMatch(key: string, term: string): number {
    const lowerKey = key.toLowerCase();
    if (!lowerKey.includes(term)) return 0;

    let score = 10;
    if (lowerKey === term || lowerKey.startsWith(term)) {
      score += 5;
    }
    return score;
  }

  private scoreTitleMatch(title: string | undefined, term: string): number {
    if (!title) return 0;

    const lowerTitle = title.toLowerCase();
    if (!lowerTitle.includes(term)) return 0;

    let score = 5;
    const words = lowerTitle.split(/\s+/);
    if (words.some((word) => word.startsWith(term))) {
      score += 2;
    }
    return score;
  }

  private scoreAuthorsMatch(
    authors: string[] | undefined,
    term: string,
  ): number {
    if (!authors) return 0;
    return authors.some((author) => author.toLowerCase().includes(term))
      ? 4
      : 0;
  }

  private scoreJournalMatch(journal: string | undefined, term: string): number {
    if (!journal) return 0;
    return journal.toLowerCase().includes(term) ? 3 : 0;
  }

  private scoreYearMatch(year: string | undefined, term: string): number {
    if (!year) return 0;
    return year === term ? 6 : 0;
  }

  private scoreAbstractMatch(
    abstract: string | undefined,
    term: string,
  ): number {
    if (!abstract) return 0;
    return abstract.toLowerCase().includes(term) ? 1 : 0;
  }
}
