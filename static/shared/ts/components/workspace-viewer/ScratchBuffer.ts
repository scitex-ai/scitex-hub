/**
 * ScratchBuffer - Manages the shared scratch buffer between user and AI.
 *
 * Responsibilities:
 * - Load/save scratch content from scitex/scratch.md via API
 * - Fall back to localStorage when no project is available
 * - Debounced server saves (1s)
 * - CSRF token extraction for POST requests
 */

import { SCRATCH_PATH } from "./TabManager.ts";
const SCRATCH_SAVE_DEBOUNCE_MS = 1000;
const SCRATCH_STORAGE_KEY = "ws-scratch-content";
const DEFAULT_CONTENT = "# CONTEXT\n\nShared workspace between you and AI.\n";

export class ScratchBuffer {
  content: string;
  private projectId: string = "";
  private saveTimer: ReturnType<typeof setTimeout> | null = null;
  private getFileUrl: (
    filePath: string,
    raw?: boolean,
    download?: boolean,
  ) => string;

  constructor(
    getFileUrl: (filePath: string, raw?: boolean, download?: boolean) => string,
  ) {
    this.getFileUrl = getFileUrl;
    this.content = localStorage.getItem(SCRATCH_STORAGE_KEY) || DEFAULT_CONTENT;
  }

  setProjectId(id: string): void {
    this.projectId = id;
    this.loadFromServer();
  }

  /** Replace scratch content entirely. */
  write(content: string): void {
    this.content = content;
    localStorage.setItem(SCRATCH_STORAGE_KEY, content);
    this.saveToServer();
  }

  /** Append text to scratch content. */
  append(text: string): void {
    this.content += text;
    localStorage.setItem(SCRATCH_STORAGE_KEY, this.content);
    this.saveToServer();
  }

  /** Sync content from the editor (called on editor change). */
  syncFromEditor(content: string): void {
    this.content = content;
    localStorage.setItem(SCRATCH_STORAGE_KEY, content);
    this.saveToServer();
  }

  /** Load scratch content from scitex/scratch.md on the server. */
  async loadFromServer(): Promise<string | null> {
    if (!this.projectId) return null;
    try {
      const url = this.getFileUrl(SCRATCH_PATH, true, false);
      const response = await fetch(url);
      if (!response.ok) return null;
      const content = await response.text();
      if (content) {
        this.content = content;
        localStorage.setItem(SCRATCH_STORAGE_KEY, content);
        return content;
      }
    } catch {
      // Server unavailable — use localStorage cache
    }
    return null;
  }

  /** Debounced save to server. */
  private saveToServer(): void {
    if (!this.projectId) return;
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(async () => {
      try {
        const csrfToken = this.getCsrfToken();
        await fetch("/api/workspace/save-file/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            project_id: this.projectId,
            path: SCRATCH_PATH,
            content: this.content,
          }),
        });
      } catch {
        // Save failed — content is still in localStorage
      }
    }, SCRATCH_SAVE_DEBOUNCE_MS);
  }

  private getCsrfToken(): string {
    return (
      document.querySelector<HTMLInputElement>(
        'input[name="csrfmiddlewaretoken"]',
      )?.value ??
      document.cookie
        .split("; ")
        .find((c) => c.startsWith("csrftoken="))
        ?.split("=")[1] ??
      ""
    );
  }
}

export { SCRATCH_PATH };
