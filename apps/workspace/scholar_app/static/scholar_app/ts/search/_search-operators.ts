/**
 * Search Operators - Shell-style query operator parsing and form application
 *
 * Syntax: -OPTION VALUE or --LONG-OPTION VALUE
 * For include/exclude: -OPTION VALUE (include) or -OPTION -VALUE (exclude with - prefix)
 *
 * Options:
 * -t | --title     Title filter (-t human = include, -t -mouse = exclude)
 * -a | --author    Author filter (-a smith = include, -a -jones = exclude)
 * -j | --journal   Journal filter (-j nature = include, -j -plos = exclude)
 * -ymin | --year-min   Minimum publication year
 * -ymax | --year-max   Maximum publication year
 * -cmin | --citations-min   Minimum citations
 * -cmax | --citations-max   Maximum citations
 * -ifmin | --if-min   Minimum impact factor
 * -ifmax | --if-max   Maximum impact factor
 *
 * Example: hippocampus -t human -t -mouse -a "john smith" -j nature -ymin 2020 -ymax 2024 -cmin 10 -ifmin 5
 */

import { applyOperatorsToForm } from "./_search-sliders";

export interface ParsedOperators {
  query: string;
  titleIncludes: string[];
  titleExcludes: string[];
  authorIncludes: string[];
  authorExcludes: string[];
  journalIncludes: string[];
  journalExcludes: string[];
  yearFrom?: number;
  yearTo?: number;
  citationsLow?: number;
  citationsHigh?: number;
  impactFactorLow?: number;
  impactFactorHigh?: number;
}

export function parseSearchOperators(input: string): ParsedOperators {
  const result: ParsedOperators = {
    query: "",
    titleIncludes: [],
    titleExcludes: [],
    authorIncludes: [],
    authorExcludes: [],
    journalIncludes: [],
    journalExcludes: [],
  };

  // Shell-style patterns: -OPTION VALUE or --LONG-OPTION VALUE
  // For text filters: value without - prefix = include, value with - prefix = exclude
  const patterns = {
    // Text filters: -t/-a/-j can have include (value) or exclude (-value)
    title: /(?:-t|--title)\s+(-?)([^\s]+|"[^"]+"|'[^']+')/gi,
    author: /(?:-a|--author)\s+(-?)([^\s]+|"[^"]+"|'[^']+')/gi,
    journal: /(?:-j|--journal)\s+(-?)([^\s]+|"[^"]+"|'[^']+')/gi,
    // Numeric filters (single value)
    yearMin: /(?:-ymin|--year-min)\s+(\d{4})/gi,
    yearMax: /(?:-ymax|--year-max)\s+(\d{4})/gi,
    citationsMin: /(?:-cmin|--citations-min)\s+(\d+)/gi,
    citationsMax: /(?:-cmax|--citations-max)\s+(\d+)/gi,
    impactFactorMin: /(?:-ifmin|--if-min)\s+(\d+(?:\.\d+)?)/gi,
    impactFactorMax: /(?:-ifmax|--if-max)\s+(\d+(?:\.\d+)?)/gi,
  };

  let remaining = input;

  // Helper to extract text filter matches (include vs exclude based on - prefix)
  const extractTextFilter = (
    pattern: RegExp,
    includes: string[],
    excludes: string[],
  ) => {
    let match;
    pattern.lastIndex = 0;
    while ((match = pattern.exec(input)) !== null) {
      const isExclude = match[1] === "-";
      const value = match[2].replace(/["']/g, "");
      if (isExclude) {
        excludes.push(value);
      } else {
        includes.push(value);
      }
      remaining = remaining.replace(match[0], "");
    }
  };

  // Helper to extract single numeric value
  const extractSingle = (pattern: RegExp): number | undefined => {
    pattern.lastIndex = 0;
    const match = pattern.exec(input);
    if (match) {
      remaining = remaining.replace(match[0], "");
      return parseFloat(match[1]);
    }
    return undefined;
  };

  // Extract text filters (include/exclude based on - prefix on value)
  extractTextFilter(patterns.title, result.titleIncludes, result.titleExcludes);
  extractTextFilter(
    patterns.author,
    result.authorIncludes,
    result.authorExcludes,
  );
  extractTextFilter(
    patterns.journal,
    result.journalIncludes,
    result.journalExcludes,
  );

  // Extract numeric filters
  result.yearFrom = extractSingle(patterns.yearMin);
  result.yearTo = extractSingle(patterns.yearMax);
  result.citationsLow = extractSingle(patterns.citationsMin);
  result.citationsHigh = extractSingle(patterns.citationsMax);
  result.impactFactorLow = extractSingle(patterns.impactFactorMin);
  result.impactFactorHigh = extractSingle(patterns.impactFactorMax);

  // Clean up remaining query
  result.query = remaining.trim().replace(/\s+/g, " ");

  return result;
}

// Initialize search operator parsing on form submit
export function initSearchOperators(): void {
  const searchForm = document.getElementById(
    "literatureSearchForm",
  ) as HTMLFormElement | null;
  const searchInput =
    document.querySelector<HTMLInputElement>('input[name="q"]');

  if (searchForm && searchInput) {
    searchForm.addEventListener("submit", (e) => {
      const operators = parseSearchOperators(searchInput.value);

      // Apply operators to form fields
      applyOperatorsToForm(operators);

      // Update search input with clean query (without operators)
      // But keep original if user wants to see what they searched
      if (operators.query !== searchInput.value) {
        // Store original in data attribute for display
        searchInput.dataset.originalQuery = searchInput.value;
      }
    });
  }
}
