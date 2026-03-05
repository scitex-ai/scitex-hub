/**
 * LocalStorage Utility Module
 * Handles persistence of application state across sessions
 */

export class StorageManager {
  private prefix: string;

  constructor(prefix: string = "scitex_") {
    this.prefix = prefix;
  }

  /**
   * Generate storage key with prefix
   */
  private getKey(key: string): string {
    return `${this.prefix}${key}`;
  }

  /**
   * Save data to localStorage (alias for setItem)
   */
  save<T>(key: string, data: T): void {
    this.setItem(key, data);
  }

  /**
   * Load data from localStorage (alias for getItem)
   */
  load<T>(key: string, defaultValue?: T): T | null {
    return this.getItem(key, defaultValue);
  }

  /**
   * Get item from localStorage with type safety
   */
  getItem<T>(key: string, defaultValue?: T): T | null {
    try {
      const fullKey = this.getKey(key);
      const data = localStorage.getItem(fullKey);
      return data ? JSON.parse(data) : defaultValue || null;
    } catch (error) {
      console.error(`[Storage] Failed to load ${key}:`, error);
      return defaultValue || null;
    }
  }

  /**
   * Set item in localStorage with type safety
   */
  setItem<T>(key: string, value: T): boolean {
    try {
      const fullKey = this.getKey(key);
      localStorage.setItem(fullKey, JSON.stringify(value));
      console.log(`[Storage] Saved: ${key}`);
      return true;
    } catch (error) {
      console.error(`[Storage] Failed to save ${key}:`, error);
      return false;
    }
  }

  /**
   * Check if key exists in localStorage
   */
  exists(key: string): boolean {
    return localStorage.getItem(this.getKey(key)) !== null;
  }

  /**
   * Check if key exists in localStorage (alias)
   */
  hasItem(key: string): boolean {
    return this.exists(key);
  }

  /**
   * Remove item from localStorage
   */
  remove(key: string): void {
    try {
      localStorage.removeItem(this.getKey(key));
      console.log(`[Storage] Removed: ${key}`);
    } catch (error) {
      console.error(`[Storage] Failed to remove ${key}:`, error);
    }
  }

  /**
   * Remove item from localStorage (alias)
   */
  removeItem(key: string): boolean {
    try {
      this.remove(key);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Clear all items with this prefix
   */
  clear(): void {
    try {
      const keys = Object.keys(localStorage);
      keys.forEach((key) => {
        if (key.startsWith(this.prefix)) {
          localStorage.removeItem(key);
        }
      });
      console.log(`[Storage] Cleared all items with prefix: ${this.prefix}`);
    } catch (error) {
      console.error("[Storage] Failed to clear storage:", error);
    }
  }

  /**
   * Get all keys stored with this prefix
   */
  getAllKeys(): string[] {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(this.prefix)) {
        keys.push(key.replace(this.prefix, ""));
      }
    }
    return keys;
  }
}

// Export singleton instances for global use
export const globalStorage = new StorageManager("scitex_");
export const writerStorage = new StorageManager("writer_app_");
