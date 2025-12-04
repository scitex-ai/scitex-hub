/**
 * Citation Completion Module
 * Handles citation autocomplete for LaTeX \cite commands
 */

import { fetchCitations } from "./CitationUtils.js";

console.log("[DEBUG] CitationCompletion.ts loaded");

/**
 * Register citation completion provider
 */
export function registerCitationCompletionProvider(monaco: any): void {
  console.log("[Citations] ========================================");
  console.log("[Citations] STARTING CITATION COMPLETION REGISTRATION");
  console.log("[Citations] ========================================");

  // Cache for citations
  let citationsCache: any[] | null = null;
  let lastFetchTime = 0;
  const CACHE_DURATION = 60000; // 1 minute

  // Register citation completion provider
  monaco.languages.registerCompletionItemProvider("latex", {
    triggerCharacters: ["{", "\\"], // Trigger on { or \ for better UX
    provideCompletionItems: async (model: any, position: any) => {
      const lineContent = model.getLineContent(position.lineNumber);
      const beforeCursor = lineContent.substring(
        0,
        position.column - 1,
      );

      console.log("[Citations] Triggered at:", beforeCursor.slice(-20));

      // Check for \cite or \cite{ context (with or without {)
      // Matches: \cite, \citep, \citet, \cite{, \citep{, \citet{
      const citeMatch = beforeCursor.match(/\\cite([tp])?\{?([^}]*)$/);
      if (!citeMatch) {
        return { suggestions: [] };
      }

      console.log("[Citations] In \\cite context!");

      const result = await fetchCitations(citationsCache, lastFetchTime, CACHE_DURATION);
      citationsCache = result.cache;
      lastFetchTime = result.fetchTime;
      const citations = result.citations;

      if (citations.length === 0) {
        console.warn(
          "[Citations] No citations available - showing guideline",
        );
        // Show helpful guideline when no citations found
        return {
          suggestions: [
            {
              label: "📚 No citations available yet",
              kind: monaco.languages.CompletionItemKind.Text,
              detail:
                "Upload BibTeX files to enable citation autocomplete",
              documentation: {
                value:
                  "To add citations:\n\n" +
                  "1. Go to Scholar app (/scholar/bibtex/)\n" +
                  "2. Upload your .bib file\n" +
                  "3. Save to this project\n" +
                  "4. Citations will appear here automatically\n\n" +
                  "Or manually add .bib files to:\n" +
                  "• scitex/scholar/bib_files/\n" +
                  "• scitex/writer/bib_files/",
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

      const currentWord = citeMatch[2] || "";

      // Fuzzy search across multiple fields
      const suggestions = citations
        .filter((cite: any) => {
          if (!currentWord) return true;
          const searchTerm = currentWord.toLowerCase();

          // Search in citation key
          if (cite.key.toLowerCase().includes(searchTerm)) return true;

          // Search in title
          if (
            cite.title &&
            cite.title.toLowerCase().includes(searchTerm)
          )
            return true;

          // Search in authors
          if (cite.authors && Array.isArray(cite.authors)) {
            if (
              cite.authors.some((author: string) =>
                author.toLowerCase().includes(searchTerm),
              )
            )
              return true;
          }

          // Search in journal
          if (
            cite.journal &&
            cite.journal.toLowerCase().includes(searchTerm)
          )
            return true;

          // Search in abstract
          if (
            cite.abstract &&
            cite.abstract.toLowerCase().includes(searchTerm)
          )
            return true;

          return false;
        })
        .map((cite: any) => {
          // Create MULTI-LINE detail showing all metadata on separate lines
          let detailLines = [];

          // Line 1: Author and Year
          if (cite.detail) {
            detailLines.push(cite.detail);
          }

          // Line 2: Title (truncated to 100 chars)
          if (cite.title) {
            const titlePreview =
              cite.title.length > 100
                ? cite.title.substring(0, 100) + "..."
                : cite.title;
            detailLines.push(`📄 ${titlePreview}`);
          }

          // Line 3: Journal with IF and Citation Count
          let metricsLine = [];
          if (cite.journal) {
            let journalPart = cite.journal;
            if (cite.impact_factor) {
              journalPart += ` (IF: ${cite.impact_factor})`;
            }
            metricsLine.push(`📖 ${journalPart}`);
          }
          if (cite.citation_count && cite.citation_count > 0) {
            metricsLine.push(`📊 ${cite.citation_count} citations`);
          }
          if (metricsLine.length > 0) {
            detailLines.push(metricsLine.join("  •  "));
          }

          // Combine all lines with newlines for multi-line display
          const detailLine = detailLines.join("\n");

          // Sort by citation count (higher first), then alphabetically
          const sortPrefix = String(
            1000000 - (cite.citation_count || 0),
          ).padStart(7, "0");

          // Build completion item with rich inline metadata
          const completionItem: any = {
            label: cite.key,
            kind: monaco.languages.CompletionItemKind.Reference,
            detail: detailLine, // All metadata visible inline
            documentation: {
              value: cite.documentation || "",
              isTrusted: false,
              supportHtml: false,
            },
            insertText: beforeCursor.endsWith("{")
              ? cite.key + "}"
              : `{${cite.key}}`, // Smart brace handling
            sortText: sortPrefix + cite.key,
            filterText: `${cite.key} ${cite.title || ""} ${cite.journal || ""} ${(cite.authors || []).join(" ")}`,
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column - currentWord.length,
              endLineNumber: position.lineNumber,
              endColumn: position.column,
            },
          };

          // Add command to show additional info on hover
          completionItem.additionalTextEdits = [];

          return completionItem;
        });

      console.log(
        `[Citations] Returning ${suggestions.length} suggestions`,
      );
      return { suggestions };
    },
  });

  console.log("[Citations] Citation completion provider registered");
}
