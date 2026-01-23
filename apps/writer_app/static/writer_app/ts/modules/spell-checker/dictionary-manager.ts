/**
 * Dictionary Manager Module
 * Handles dictionary loading and Typo.js initialization
 */

// Import Typo.js - it's a UMD module, so we access it from window
declare global {
  interface Window {
    Typo: any;
  }
}

export class DictionaryManager {
  private dictionary: any = null;
  private dictionaryLoading: boolean = false;
  private dictionaryLoaded: boolean = false;
  private language: string;

  constructor(language: string = 'en-US') {
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
    console.log('[DictionaryManager] Loading dictionary files...');

    try {
      const lang = this.language.replace('-', '_'); // en-US -> en_US
      const basePath = '/static/writer_app/dictionaries';

      // Load .aff and .dic files
      const [affResponse, dicResponse] = await Promise.all([
        fetch(`${basePath}/${lang}.aff`),
        fetch(`${basePath}/${lang}.dic`)
      ]);

      if (!affResponse.ok || !dicResponse.ok) {
        throw new Error(`Failed to load dictionary files: ${affResponse.status}, ${dicResponse.status}`);
      }

      const affData = await affResponse.text();
      const dicData = await dicResponse.text();

      // Check if Typo is available
      if (!window.Typo) {
        console.error('[DictionaryManager] Typo.js not loaded! Loading from CDN...');
        await this.loadTypoFromCDN();
      }

      // Initialize Typo dictionary
      this.dictionary = new window.Typo(lang, affData, dicData);
      this.dictionaryLoaded = true;
      this.dictionaryLoading = false;

      console.log('[DictionaryManager] ✓ Dictionary loaded successfully');
    } catch (error) {
      console.error('[DictionaryManager] Failed to load dictionary:', error);
      console.warn('[DictionaryManager] Falling back to permissive mode');
      this.dictionaryLoading = false;
    }
  }

  /**
   * Load Typo.js from CDN if not already available
   */
  private async loadTypoFromCDN(): Promise<void> {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/typo-js@1.2.4/typo.js';
      script.onload = () => {
        console.log('[DictionaryManager] Typo.js loaded from CDN');
        resolve();
      };
      script.onerror = () => {
        reject(new Error('Failed to load Typo.js from CDN'));
      };
      document.head.appendChild(script);
    });
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
