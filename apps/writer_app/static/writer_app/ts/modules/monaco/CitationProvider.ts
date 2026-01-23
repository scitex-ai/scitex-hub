/**
 * Citation Autocomplete Provider
 * Provides citation key suggestions from BibTeX files
 */

export class CitationProvider {
  private citationsCache: any[] | null = null;
  private lastFetchTime = 0;
  private readonly CACHE_DURATION = 60000; // 1 minute

  /**
   * Get project ID from various sources
   */
  private getProjectId(): string | null {
    const writerConfig = (window as any).WRITER_CONFIG;
    if (writerConfig?.projectId) return String(writerConfig.projectId);

    const match = window.location.pathname.match(/\/writer\/project\/(\d+)\//);
    if (match) return match[1];

    if ((window as any).SCITEX_PROJECT_ID) {
      return String((window as any).SCITEX_PROJECT_ID);
    }

    console.warn("[Citations] No project ID found");
    return null;
  }

  /**
   * Fetch citations from API with caching
   */
  private async fetchCitations(): Promise<any[]> {
    const projectId = this.getProjectId();
    if (!projectId) return [];

    const now = Date.now();
    if (this.citationsCache && now - this.lastFetchTime < this.CACHE_DURATION) {
      return this.citationsCache;
    }

    try {
      const apiUrl = `/writer/api/project/${projectId}/citations/`;
      const response = await fetch(apiUrl);

      if (!response.ok) return [];

      const data = await response.json();

      if (data.success && data.citations) {
        this.citationsCache = data.citations;
        this.lastFetchTime = now;
        return data.citations;
      }
      return [];
    } catch (error) {
      console.error("[Citations] Error fetching:", error);
      return [];
    }
  }

  /**
   * Register citation completion provider
   */
  public register(monaco: any): void {
    monaco.languages.registerCompletionItemProvider("latex", {
      triggerCharacters: ["{", "\\"],
      provideCompletionItems: async (model: any, position: any) => {
        const lineContent = model.getLineContent(position.lineNumber);
        const beforeCursor = lineContent.substring(0, position.column - 1);

        const citeMatch = beforeCursor.match(/\\cite([tp])?\{?([^}]*)$/);
        if (!citeMatch) return { suggestions: [] };

        const citations = await this.fetchCitations();
        if (citations.length === 0) {
          return this.getNoResultsSuggestion(monaco, position);
        }

        return this.buildSuggestions(monaco, citations, citeMatch, beforeCursor, position);
      },
    });
  }

  /**
   * Build suggestion when no citations available
   */
  private getNoResultsSuggestion(monaco: any, position: any): any {
    return {
      suggestions: [
        {
          label: "No citations available yet",
          kind: monaco.languages.CompletionItemKind.Text,
          detail: "Upload BibTeX files to enable citation autocomplete",
          documentation: {
            value:
              "To add citations:\n\n" +
              "1. Go to Scholar app (/scholar/bibtex/)\n" +
              "2. Upload your .bib file\n" +
              "3. Save to this project\n" +
              "4. Citations will appear here automatically\n\n" +
              "Or manually add .bib files to:\n" +
              "- scitex/scholar/bib_files/\n" +
              "- scitex/writer/bib_files/",
            isTrusted: true,
            supportHtml: false,
          },
          insertText: "",
          range: {
            startLineNumber: position.lineNumber,
            startColumn: position.column,
            endLineNumber: position.lineNumber,
            endColumn: position.column,
          },
        },
      ],
    };
  }

  /**
   * Build citation suggestions from data
   */
  private buildSuggestions(
    monaco: any,
    citations: any[],
    citeMatch: RegExpMatchArray,
    beforeCursor: string,
    position: any,
  ): any {
    const currentWord = citeMatch[2] || "";

    // Fuzzy search across multiple fields
    const suggestions = citations
      .filter((cite: any) => {
        if (!currentWord) return true;
        const searchTerm = currentWord.toLowerCase();

        return (
          cite.key.toLowerCase().includes(searchTerm) ||
          (cite.title && cite.title.toLowerCase().includes(searchTerm)) ||
          (cite.journal && cite.journal.toLowerCase().includes(searchTerm)) ||
          (cite.abstract && cite.abstract.toLowerCase().includes(searchTerm)) ||
          (cite.authors &&
            Array.isArray(cite.authors) &&
            cite.authors.some((author: string) =>
              author.toLowerCase().includes(searchTerm),
            ))
        );
      })
      .map((cite: any) => {
        // Build multi-line detail
        const detailLines = [];

        if (cite.detail) {
          detailLines.push(cite.detail);
        }

        if (cite.title) {
          const titlePreview =
            cite.title.length > 100
              ? cite.title.substring(0, 100) + "..."
              : cite.title;
          detailLines.push(`${titlePreview}`);
        }

        const metricsLine = [];
        if (cite.journal) {
          let journalPart = cite.journal;
          if (cite.impact_factor) {
            journalPart += ` (IF: ${cite.impact_factor})`;
          }
          metricsLine.push(journalPart);
        }
        if (cite.citation_count && cite.citation_count > 0) {
          metricsLine.push(`${cite.citation_count} citations`);
        }
        if (metricsLine.length > 0) {
          detailLines.push(metricsLine.join(" - "));
        }

        const detailLine = detailLines.join("\n");

        // Sort by citation count (higher first)
        const sortPrefix = String(1000000 - (cite.citation_count || 0)).padStart(
          7,
          "0",
        );

        return {
          label: cite.key,
          kind: monaco.languages.CompletionItemKind.Reference,
          detail: detailLine,
          documentation: {
            value: cite.documentation || "",
            isTrusted: false,
            supportHtml: false,
          },
          insertText: beforeCursor.endsWith("{")
            ? cite.key + "}"
            : `{${cite.key}}`,
          sortText: sortPrefix + cite.key,
          filterText: `${cite.key} ${cite.title || ""} ${cite.journal || ""} ${(cite.authors || []).join(" ")}`,
          range: {
            startLineNumber: position.lineNumber,
            startColumn: position.column - currentWord.length,
            endLineNumber: position.lineNumber,
            endColumn: position.column,
          },
        };
      });

    console.log(`[Citations] Returning ${suggestions.length} suggestions`);
    return { suggestions };
  }

  /**
   * Register hover provider for citations
   */
  public registerHoverProvider(monaco: any): void {
    monaco.languages.registerHoverProvider("latex", {
      provideHover: async (model: any, position: any) => {
        const lineContent = model.getLineContent(position.lineNumber);
        const word = model.getWordAtPosition(position);
        if (!word) return null;

        const beforeWord = lineContent.substring(0, position.column - 1);
        const afterWord = lineContent.substring(position.column - 1);

        const beforeMatch = beforeWord.match(/\\cite[tp]?\{([^}]*)$/);
        const afterMatch = afterWord.match(/^([^}]*)\}/);
        if (!beforeMatch && !afterMatch) return null;

        const citations = await this.fetchCitations();
        const citation = citations.find((c: any) => c.key === word.word);
        if (!citation) return null;

        return {
          contents: [
            { value: `**${citation.key}**` },
            { value: citation.documentation || "" },
          ],
        };
      },
    });
  }
}
