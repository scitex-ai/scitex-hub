/**
 * Word Checker Module
 * Validates word spelling using Typo.js dictionary and heuristics
 */

export class WordChecker {
  private spellingCache: Map<string, boolean> = new Map();
  private customWords: Set<string> = new Set();

  constructor(customWords: Set<string> = new Set()) {
    this.customWords = customWords;
  }

  /**
   * Check if a word is spelled correctly
   */
  async isWordCorrect(
    word: string,
    dictionary: any,
    dictionaryLoaded: boolean
  ): Promise<boolean> {
    // Skip very short words (1-2 chars)
    if (word.length <= 2) return true;

    // Skip capitalized words (likely proper nouns)
    if (word[0] === word[0].toUpperCase() && word.slice(1) === word.slice(1).toLowerCase()) {
      return true;
    }

    // Check custom dictionary
    if (this.customWords.has(word.toLowerCase())) {
      return true;
    }

    // Check cache
    const cacheKey = word.toLowerCase();
    if (this.spellingCache.has(cacheKey)) {
      return this.spellingCache.get(cacheKey)!;
    }

    // Use browser's experimental spell check API if available
    const isCorrect = await this.checkWordWithBrowser(word, dictionary, dictionaryLoaded);

    // Cache result
    this.spellingCache.set(cacheKey, isCorrect);

    return isCorrect;
  }

  /**
   * Check word using Typo.js dictionary
   */
  private async checkWordWithBrowser(
    word: string,
    dictionary: any,
    dictionaryLoaded: boolean
  ): Promise<boolean> {
    const lowerWord = word.toLowerCase();

    // Skip very short words (likely articles, prepositions)
    if (word.length <= 2) {
      return true;
    }

    // Accept words with numbers (like "figure1", "table2", "2020")
    if (/\d/.test(word)) {
      return true;
    }

    // Accept hyphenated words - check each part separately
    if (word.includes('-')) {
      const parts = word.split('-');
      // If all parts are valid, accept the whole word
      for (const part of parts) {
        if (part.length > 2 && dictionary && !dictionary.check(part)) {
          // Check each part, but be lenient
          return true; // Accept hyphenated words for now
        }
      }
      return true;
    }

    // Use Typo.js dictionary if loaded
    if (dictionary && dictionaryLoaded) {
      return dictionary.check(word);
    }

    // Dictionary not loaded yet - be permissive to avoid false positives
    // Accept words ending in common suffixes
    const commonSuffixes = [
      'ing', 'ed', 'er', 'est', 'ly', 'tion', 'sion', 'ment', 'ness', 'ity', 'ful',
      'less', 'ous', 'ive', 'able', 'ible', 'al', 'ic', 'ical', 'ize', 'ise',
      'ized', 'ised', 'izing', 'ising', 'ization', 'isation'
    ];

    if (commonSuffixes.some(suffix => lowerWord.endsWith(suffix))) {
      return true;
    }

    // Accept words starting with common prefixes
    const commonPrefixes = [
      'un', 're', 'pre', 'post', 'non', 'anti', 'de', 'dis', 'en', 'em',
      'fore', 'in', 'im', 'inter', 'mid', 'mis', 'over', 'out', 'super',
      'trans', 'under', 'sub', 'co', 'multi', 'semi', 'auto', 'bio', 'micro',
      'macro', 'nano', 'neuro', 'psycho', 'photo', 'electro', 'hydro', 'geo'
    ];

    if (commonPrefixes.some(prefix => lowerWord.startsWith(prefix) && lowerWord.length > prefix.length + 2)) {
      return true;
    }

    // Common misspelling patterns - flag these as errors even without dictionary
    const commonMisspellings = new Set([
      'teh', 'adn', 'taht', 'thsi', 'fo', 'waht', 'wiht', 'wtih',
      'recieve', 'recieved', 'occured', 'occuring', 'seperate', 'definately',
      'goverment', 'enviroment', 'recomend', 'begining', 'untill',
      'wich', 'wether', 'wheather', 'beleive', 'belive'
    ]);

    if (commonMisspellings.has(lowerWord)) {
      return false;
    }

    // Fallback: accept most words while dictionary is loading
    return true;
  }

  /**
   * Clear the spelling cache
   */
  clearCache(): void {
    this.spellingCache.clear();
  }

  /**
   * Get custom words set
   */
  getCustomWords(): Set<string> {
    return this.customWords;
  }

  /**
   * Set custom words
   */
  setCustomWords(words: Set<string>): void {
    this.customWords = words;
    this.clearCache(); // Clear cache when custom dictionary changes
  }

  /**
   * Add a word to custom dictionary
   */
  addCustomWord(word: string): void {
    this.customWords.add(word.toLowerCase());
    this.spellingCache.set(word.toLowerCase(), true);
  }
}
