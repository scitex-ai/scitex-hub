/**
 * LaTeX Parser Module
 * Extracts checkable regions from LaTeX content, skipping commands, math mode, etc.
 */

import type { CheckableRegion, ExtractedWord, TextRange } from './types';

export class LaTeXParser {
  // LaTeX patterns to skip
  private readonly LATEX_COMMAND_REGEX = /\\[a-zA-Z@]+/g;
  private readonly LATEX_INLINE_MATH = /\$[^$]+\$/g;
  private readonly LATEX_DISPLAY_MATH = /\$\$[^$]+\$\$/g;
  private readonly LATEX_ENV_MATH = /\\begin\{(equation|align|gather|multline|displaymath)\*?\}[\s\S]*?\\end\{\1\*?\}/g;
  private readonly CITATION_REGEX = /\\cite[tp]?\{[^}]+\}/g;
  private readonly REF_REGEX = /\\(ref|label|eqref)\{[^}]+\}/g;

  constructor(
    private skipLaTeXCommands: boolean = true,
    private skipMathMode: boolean = true,
    private skipCodeBlocks: boolean = true
  ) {}

  /**
   * Extract regions of text that should be spell-checked
   * (skipping LaTeX commands, math mode, etc.)
   */
  extractCheckableRegions(content: string): CheckableRegion[] {
    const regions: CheckableRegion[] = [];

    // Build list of ranges to skip
    const skipRanges: TextRange[] = [];

    if (this.skipLaTeXCommands) {
      // Skip LaTeX commands
      let match;
      const commandRegex = new RegExp(this.LATEX_COMMAND_REGEX.source, 'g');
      while ((match = commandRegex.exec(content)) !== null) {
        skipRanges.push({ start: match.index, end: match.index + match[0].length });
      }
    }

    if (this.skipMathMode) {
      // Skip inline math
      let match;
      const inlineMathRegex = new RegExp(this.LATEX_INLINE_MATH.source, 'g');
      while ((match = inlineMathRegex.exec(content)) !== null) {
        skipRanges.push({ start: match.index, end: match.index + match[0].length });
      }

      // Skip display math
      const displayMathRegex = new RegExp(this.LATEX_DISPLAY_MATH.source, 'g');
      while ((match = displayMathRegex.exec(content)) !== null) {
        skipRanges.push({ start: match.index, end: match.index + match[0].length });
      }

      // Skip math environments
      const envMathRegex = new RegExp(this.LATEX_ENV_MATH.source, 'g');
      while ((match = envMathRegex.exec(content)) !== null) {
        skipRanges.push({ start: match.index, end: match.index + match[0].length });
      }
    }

    // Skip citations and references
    const citationRegex = new RegExp(this.CITATION_REGEX.source, 'g');
    let match;
    while ((match = citationRegex.exec(content)) !== null) {
      skipRanges.push({ start: match.index, end: match.index + match[0].length });
    }

    const refRegex = new RegExp(this.REF_REGEX.source, 'g');
    while ((match = refRegex.exec(content)) !== null) {
      skipRanges.push({ start: match.index, end: match.index + match[0].length });
    }

    // Sort and merge overlapping ranges
    skipRanges.sort((a, b) => a.start - b.start);
    const mergedSkipRanges = this.mergeRanges(skipRanges);

    // Extract checkable regions (everything not in skip ranges)
    let currentPos = 0;
    for (const skipRange of mergedSkipRanges) {
      if (currentPos < skipRange.start) {
        const text = content.substring(currentPos, skipRange.start);
        regions.push({ text, startOffset: currentPos });
      }
      currentPos = skipRange.end;
    }

    // Add final region
    if (currentPos < content.length) {
      const text = content.substring(currentPos);
      regions.push({ text, startOffset: currentPos });
    }

    return regions;
  }

  /**
   * Merge overlapping ranges
   */
  mergeRanges(ranges: TextRange[]): TextRange[] {
    if (ranges.length === 0) return [];

    const merged: TextRange[] = [ranges[0]];

    for (let i = 1; i < ranges.length; i++) {
      const current = ranges[i];
      const last = merged[merged.length - 1];

      if (current.start <= last.end) {
        // Overlapping, merge
        last.end = Math.max(last.end, current.end);
      } else {
        // Non-overlapping, add new range
        merged.push(current);
      }
    }

    return merged;
  }

  /**
   * Extract individual words from text
   */
  extractWords(text: string): ExtractedWord[] {
    const words: ExtractedWord[] = [];

    // Match words (including contractions like "don't", "it's")
    const wordRegex = /\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b/g;
    let match;

    while ((match = wordRegex.exec(text)) !== null) {
      words.push({
        text: match[0],
        startIndex: match.index,
        endIndex: match.index + match[0].length,
      });
    }

    return words;
  }
}
