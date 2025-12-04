/**
 * Spell Check Integration Module
 * Manages spell checking functionality
 */

import { SpellChecker } from "../spell-checker.js";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/monaco-editor/spell-check-integration.ts loaded",
);

export class SpellCheckIntegration {
  private spellChecker?: SpellChecker;

  constructor(spellChecker: SpellChecker | undefined) {
    this.spellChecker = spellChecker;
  }

  /**
   * Enable spell checking
   */
  enableSpellCheck(): void {
    if (this.spellChecker) {
      this.spellChecker.enable();
      console.log("[Editor] Spell check enabled");
    }
  }

  /**
   * Disable spell checking
   */
  disableSpellCheck(): void {
    if (this.spellChecker) {
      this.spellChecker.disable();
      console.log("[Editor] Spell check disabled");
    }
  }

  /**
   * Re-check all content for spelling errors
   */
  recheckSpelling(): void {
    if (this.spellChecker) {
      this.spellChecker.recheckAll();
      console.log("[Editor] Re-checking all content");
    }
  }

  /**
   * Add word to custom dictionary
   */
  addToSpellCheckDictionary(word: string): void {
    if (this.spellChecker) {
      this.spellChecker.addToCustomDictionary(word);
    }
  }

  /**
   * Clear custom spell check dictionary
   */
  clearSpellCheckDictionary(): void {
    if (this.spellChecker) {
      this.spellChecker.clearCustomDictionary();
    }
  }
}
