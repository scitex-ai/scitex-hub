/**
 * Citation Hover Module
 * Provides tooltip information when hovering over citations
 */

import { fetchCitations } from "./CitationUtils.js";

console.log("[DEBUG] CitationHover.ts loaded");

/**
 * Register citation hover provider
 */
export function registerCitationHoverProvider(monaco: any): void {
  console.log("[Citations] Registering hover provider...");

  // Cache for citations (shared with completion provider via closure)
  let citationsCache: any[] | null = null;
  let lastFetchTime = 0;
  const CACHE_DURATION = 60000; // 1 minute

  monaco.languages.registerHoverProvider("latex", {
    provideHover: async (model: any, position: any) => {
      const lineContent = model.getLineContent(position.lineNumber);
      const word = model.getWordAtPosition(position);

      if (!word) return null;

      // Check if we're hovering over a citation key inside \cite{}
      const beforeWord = lineContent.substring(0, position.column - 1);
      const afterWord = lineContent.substring(position.column - 1);

      // Match: \cite{WORD} or \citep{WORD} or \citet{WORD}
      const beforeMatch = beforeWord.match(/\\cite[tp]?\{([^}]*)$/);
      const afterMatch = afterWord.match(/^([^}]*)\}/);

      if (!beforeMatch && !afterMatch) return null;

      // Get the citation key under cursor
      const citationKey = word.word;
      console.log(
        "[Citations] Hovering over citation key:",
        citationKey,
      );

      // Fetch citations and find matching key
      const result = await fetchCitations(citationsCache, lastFetchTime, CACHE_DURATION);
      citationsCache = result.cache;
      lastFetchTime = result.fetchTime;
      const citations = result.citations;

      const citation = citations.find(
        (c: any) => c.key === citationKey,
      );

      if (!citation) {
        console.log(
          "[Citations] Key not found in bibliography:",
          citationKey,
        );
        return null;
      }

      console.log(
        "[Citations] Found citation for hover:",
        citation.key,
      );

      // Return rich hover content
      return {
        contents: [
          { value: `**${citation.key}**` },
          { value: citation.documentation || "" },
        ],
      };
    },
  });

  console.log("[Citations] Hover provider registered");
}
