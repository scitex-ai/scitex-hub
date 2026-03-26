/**
 * Collaborative Editor Manager
 * Handles manuscript editing, collaboration, auto-save, word counts, and version control.
 * Integrates WriterWSClient for real-time WebSocket collaboration.
 *
 * @version 3.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

import type { ManuscriptConfig, CursorPosition } from "./types";
import { ChangeTracker } from "./changes";
import { CursorManager } from "./cursors";
import { SyncManager } from "./sync";
import { WriterWSClient } from "./ws-client";
import {
  handleCollaboratorsList,
  handleUserJoined,
  handleUserLeft,
  handleRemoteCursorUpdate,
  handleSectionLocked,
  handleSectionUnlocked,
  handleConnectionChange,
} from "../../collaboration-panel";

export class CollaborativeEditorManager {
  private changeTracker: ChangeTracker;
  private cursorManager: CursorManager;
  private syncManager: SyncManager;
  private wsClient: WriterWSClient;

  constructor(private manuscriptConfig: ManuscriptConfig) {
    this.changeTracker = new ChangeTracker(manuscriptConfig);
    this.cursorManager = new CursorManager(
      manuscriptConfig,
      this.changeTracker,
    );
    this.syncManager = new SyncManager(manuscriptConfig);
    this.wsClient = new WriterWSClient(manuscriptConfig.id);
  }

  /**
   * Initialize the editor
   */
  initialize(): void {
    console.log("[CollabEditor] Initializing collaborative editor");

    this.setupEditorListeners();
    this.syncManager.setupAutoSave();
    this.syncManager.loadSavedContent();
    this.changeTracker.updateWordCounts();
    this.changeTracker.updateProgress();
    this.setupWebSocket();

    console.log("[CollabEditor] Initialization complete");
  }

  /**
   * Setup event listeners for all section textareas
   */
  private setupEditorListeners(): void {
    this.manuscriptConfig.sections.forEach((section) => {
      const textarea = document.getElementById(
        `section-${section}`,
      ) as HTMLTextAreaElement;
      if (textarea) {
        textarea.addEventListener("input", () => {
          this.changeTracker.updateWordCount(section);

          const wordCount = this.changeTracker.countWords(textarea.value);
          this.cursorManager.updateSectionBadge(section, wordCount);

          this.changeTracker.updateProgress();
          this.changeTracker.markAsModified();

          // Broadcast text change to collaborators
          if (this.cursorManager.isEnabled()) {
            this.wsClient.sendTextChange(
              section,
              { type: "replace", content: textarea.value },
              0,
            );
          }
        });

        // Track cursor position changes and broadcast them
        const sendCursor = (): void => {
          if (!this.cursorManager.isEnabled()) return;
          const pos = this.getCursorPosition(textarea);
          this.wsClient.sendCursorPosition(section, pos);
        };
        textarea.addEventListener("click", sendCursor);
        textarea.addEventListener("keyup", sendCursor);
        textarea.addEventListener("select", sendCursor);

        // Auto-lock section on focus, unlock on blur
        textarea.addEventListener("focus", () => {
          if (this.cursorManager.isEnabled()) {
            this.wsClient.sendSectionLock(section);
          }
        });
        textarea.addEventListener("blur", () => {
          if (this.cursorManager.isEnabled()) {
            this.wsClient.sendSectionUnlock(section);
          }
        });
      }
    });
  }

  /**
   * Wire up the WebSocket client to collaboration-panel and cursor rendering.
   */
  private setupWebSocket(): void {
    this.wsClient.subscribe({
      onCollaboratorsList: (collabs) => {
        handleCollaboratorsList(collabs);
      },

      onUserJoined: (userId, username) => {
        handleUserJoined(userId, username);
      },

      onUserLeft: (userId, username) => {
        handleUserLeft(userId, username);
        this.cursorManager.removeRemoteCursor(userId);
      },

      onCursorUpdate: (userId, username, section, position) => {
        this.cursorManager.updateRemoteCursor(
          userId,
          username,
          section,
          position,
        );
        handleRemoteCursorUpdate(userId, username, section);
      },

      onSectionLocked: (userId, username, section) => {
        handleSectionLocked(userId, username, section);
        this.applySectionLockUI(section, username);
      },

      onSectionUnlocked: (userId, username, section) => {
        handleSectionUnlocked(userId, username, section);
        this.removeSectionLockUI(section);
      },

      onTextChange: (_userId, section, _sectionId, operation) => {
        if (section) {
          this.applyRemoteTextChange(section, operation);
        }
      },

      onLockFailed: (section, message) => {
        console.warn("[CollabEditor] Lock failed for", section, message);
      },

      onConnectionChange: (connected) => {
        handleConnectionChange(connected);
        if (!connected) {
          this.cursorManager.removeAllCursors();
        }
      },
    });

    // Connect immediately -- the server will send collaborators_list on open
    this.wsClient.connect();
  }

  // ------------------------------------------------ cursor position helper

  private getCursorPosition(textarea: HTMLTextAreaElement): CursorPosition {
    const offset = textarea.selectionStart;
    const textBefore = textarea.value.substring(0, offset);
    const lines = textBefore.split("\n");
    return {
      line: lines.length - 1,
      ch: lines[lines.length - 1].length,
      offset,
    };
  }

  // --------------------------------------------- remote change application

  /**
   * Apply an incoming text change from another user.
   * Currently handles full-replace operations.
   */
  private applyRemoteTextChange(section: string, operation: unknown): void {
    const textarea = document.getElementById(
      `section-${section}`,
    ) as HTMLTextAreaElement | null;
    if (!textarea) return;

    const op = operation as { type?: string; content?: string };
    if (op.type === "replace" && typeof op.content === "string") {
      // Preserve local cursor position across the remote update
      const selStart = textarea.selectionStart;
      const selEnd = textarea.selectionEnd;
      textarea.value = op.content;
      textarea.selectionStart = Math.min(selStart, op.content.length);
      textarea.selectionEnd = Math.min(selEnd, op.content.length);

      // Update word count display
      this.changeTracker.updateWordCount(section);
      const wordCount = this.changeTracker.countWords(textarea.value);
      this.cursorManager.updateSectionBadge(section, wordCount);
      this.changeTracker.updateProgress();
    }
  }

  // ------------------------------------------------ section lock UI helpers

  private applySectionLockUI(section: string, lockedBy: string): void {
    const textarea = document.getElementById(
      `section-${section}`,
    ) as HTMLTextAreaElement | null;
    if (!textarea) return;

    // Do not disable if the current user holds the lock
    const config = (window as any).WRITER_CONFIG;
    const myUsername = config?.username || config?.visitorUsername || "";
    if (lockedBy === myUsername) return;

    textarea.classList.add("section-locked");
    textarea.setAttribute("data-locked-by", lockedBy);
    textarea.title = `Locked by ${lockedBy}`;
  }

  private removeSectionLockUI(section: string): void {
    const textarea = document.getElementById(
      `section-${section}`,
    ) as HTMLTextAreaElement | null;
    if (!textarea) return;

    textarea.classList.remove("section-locked");
    textarea.removeAttribute("data-locked-by");
    textarea.title = "";
  }

  // --------------------------------------------------------- public methods

  setupCollaborationToggle(): void {
    this.cursorManager.setupCollaborationToggle();
  }

  exportJSON(): void {
    this.syncManager.exportJSON();
  }

  showLatexView(): void {
    alert(
      "LaTeX view coming soon! This will show the generated LaTeX code for your manuscript.",
    );
  }

  compileManuscript(): void {
    alert(
      "PDF compilation coming soon! This will generate a PDF from your manuscript.",
    );
  }

  openVersionControl(): void {
    window.location.href = `/apps/writer/version-control/${this.manuscriptConfig.id}/`;
  }

  async createVersion(): Promise<void> {
    await this.syncManager.createVersion();
  }

  /** Expose the WebSocket client for advanced usage. */
  getWSClient(): WriterWSClient {
    return this.wsClient;
  }

  destroy(): void {
    this.wsClient.disconnect();
    this.cursorManager.removeAllCursors();
    this.syncManager.destroy();
    console.log("[CollabEditor] Editor manager destroyed");
  }
}
