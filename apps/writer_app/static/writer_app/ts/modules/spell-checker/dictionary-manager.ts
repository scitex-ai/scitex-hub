/**
 * Dictionary Manager Module
 * Handles dictionary loading and Typo.js initialization
 */

// Import Typo.js directly from npm package (bundled by Vite)
// @ts-ignore — typo-js has no type declarations
import Typo from "typo-js";

export class DictionaryManager {
  private dictionary: any = null;
  private dictionaryLoading: boolean = false;
  private dictionaryLoaded: boolean = false;
  private language: string;

  constructor(language: string = "en-US") {
    this.language = language;
  }

  /**
   * Initialize Typo.js dictionary by loading .aff and .dic files
   */
  async initializeDictionary(): Promise<void> {
    if (this.dictionaryLoading || this.dictionaryLoaded) {
      return;
    }

    this.dictionaryLoading = true;
    console.log("[DictionaryManager] Loading dictionary files...");

    try {
      const lang = this.language.replace("-", "_"); // en-US -> en_US
      const basePath = "/static/writer_app/dictionaries";

      // Load .aff and .dic files
      const [affResponse, dicResponse] = await Promise.all([
        fetch(`${basePath}/${lang}.aff`),
        fetch(`${basePath}/${lang}.dic`),
      ]);

      if (!affResponse.ok || !dicResponse.ok) {
        throw new Error(
          `Failed to load dictionary files: ${affResponse.status}, ${dicResponse.status}`,
        );
      }

      const affData = await affResponse.text();
      const dicData = await dicResponse.text();

      // Initialize Typo dictionary (Typo is imported directly from npm)
      this.dictionary = new Typo(lang, affData, dicData);
      this.dictionaryLoaded = true;
      this.dictionaryLoading = false;

      console.log("[DictionaryManager] Dictionary loaded successfully");
    } catch (error) {
      console.error("[DictionaryManager] Failed to load dictionary:", error);
      this.dictionaryLoading = false;
    }
  }

  /**
   * Check if dictionary is loaded
   */
  isLoaded(): boolean {
    return this.dictionaryLoaded;
  }

  /**
   * Check if dictionary is currently loading
   */
  isLoading(): boolean {
    return this.dictionaryLoading;
  }

  /**
   * Get the dictionary instance
   */
  getDictionary(): any {
    return this.dictionary;
  }
}
