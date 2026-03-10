/**
 * Spell Checker Type Definitions
 */

export interface SpellCheckConfig {
  enabled: boolean;
  language: string; // e.g., 'en-US', 'en-GB'
  skipLaTeXCommands: boolean;
  skipMathMode: boolean;
  skipCodeBlocks: boolean;
  customDictionary?: string[]; // Words to always consider correct
}

export interface CheckableRegion {
  text: string;
  startOffset: number;
}

export interface ExtractedWord {
  text: string;
  startIndex: number;
  endIndex: number;
}

export interface TextRange {
  start: number;
  end: number;
}
