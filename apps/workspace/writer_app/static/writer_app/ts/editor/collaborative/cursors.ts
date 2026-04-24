/**
 * Cursor and Collaboration Mode Management
 *
 * Renders remote collaborator cursors as CSS overlays on section textareas
 * and manages the collaboration toggle UI.
 *
 * @version 3.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

import type { ManuscriptConfig, CursorPosition } from "./types";
import { ChangeTracker } from "./changes";

/** Colours assigned to remote users (deterministic by username hash). */
const CURSOR_COLORS = [
  "#54aeff",
  "#ff6b6b",
  "#51cf66",
  "#ffa94d",
  "#845ef7",
  "#ff8787",
  "#5c7cfa",
  "#69db7c",
];

function colorForUser(username: string): string {
  const hash = username
    .split("")
    .reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  return CURSOR_COLORS[hash % CURSOR_COLORS.length];
}

/** State kept for each visible remote cursor. */
interface RemoteCursorState {
  username: string;
  section: string;
  position: CursorPosition;
  element: HTMLElement;
  labelElement: HTMLElement;
}

export class CursorManager {
  private isCollaborationEnabled = false;
  /** Map from user_id to the overlay state for that remote cursor. */
  private remoteCursors: Map<number, RemoteCursorState> = new Map();

  constructor(
    private manuscriptConfig: ManuscriptConfig,
    private changeTracker: ChangeTracker,
  ) {}

  // ------------------------------------------------------ collaboration mode

  isEnabled(): boolean {
    return this.isCollaborationEnabled;
  }

  setupCollaborationToggle(): void {
    const toggle = document.getElementById("collaboration-toggle");
    if (!toggle) {
      console.warn("[CollabEditor] Collaboration toggle not found");
      return;
    }
    toggle.addEventListener("click", () => {
      if (!this.isCollaborationEnabled) {
        this.enableCollaboration();
      } else {
        this.disableCollaboration();
      }
    });
  }

  enableCollaboration(): void {
    this.isCollaborationEnabled = true;
    const toggle = document.getElementById("collaboration-toggle");
    const status = document.getElementById("collab-status");
    const info = document.getElementById("collaboration-info");

    if (toggle) {
      toggle.classList.add("active");
      toggle.innerHTML = '<i class="fas fa-users"></i> Collaboration Active';
    }
    if (status) status.classList.remove("hidden");
    if (info) info.classList.remove("hidden");

    document.querySelectorAll(".collaborative-help").forEach((help) => {
      help.classList.remove("hidden");
    });
    document.querySelectorAll(".text-editor").forEach((editor) => {
      editor.classList.add("collaborative-editing");
    });

    if ((window as any).collaborativeEditor) {
      console.log("[CollabEditor] Collaborative editing enabled");
    }

    this.manuscriptConfig.sections.forEach((section) => {
      const textarea = document.getElementById(
        `section-${section}`,
      ) as HTMLTextAreaElement;
      if (textarea) {
        const wordCount = this.changeTracker.countWords(textarea.value);
        this.updateSectionBadge(section, wordCount);
      }
    });
  }

  disableCollaboration(): void {
    this.isCollaborationEnabled = false;
    const toggle = document.getElementById("collaboration-toggle");
    const status = document.getElementById("collab-status");
    const info = document.getElementById("collaboration-info");

    if (toggle) {
      toggle.classList.remove("active");
      toggle.innerHTML = '<i class="fas fa-users"></i> Enable Collaboration';
    }
    if (status) status.classList.add("hidden");
    if (info) info.classList.add("hidden");

    document.querySelectorAll(".collaborative-help").forEach((help) => {
      help.classList.add("hidden");
    });
    document.querySelectorAll(".text-editor").forEach((editor) => {
      editor.classList.remove("collaborative-editing");
    });

    if ((window as any).collaborativeEditor) {
      (window as any).collaborativeEditor.destroy();
      console.log("[CollabEditor] Collaborative editing disabled");
    }

    // Remove all remote cursor overlays
    this.removeAllCursors();

    this.manuscriptConfig.sections.forEach((section) => {
      const textarea = document.getElementById(
        `section-${section}`,
      ) as HTMLTextAreaElement;
      if (textarea) {
        const wordCount = this.changeTracker.countWords(textarea.value);
        this.updateSectionBadge(section, wordCount);
      }
    });
  }

  // ----------------------------------------------------- section badge logic

  updateSectionBadge(section: string, wordCount: number): void {
    const badgesContainer = document.getElementById(`${section}-badges`);
    if (!badgesContainer) return;

    badgesContainer.innerHTML = "";

    if (wordCount > 0) {
      const badge = document.createElement("span");
      badge.className = "collaboration-badge active";
      badge.innerHTML = `<i class="fas fa-edit"></i> ${wordCount} words`;
      badgesContainer.appendChild(badge);
    }

    if (this.isCollaborationEnabled) {
      const collabBadge = document.createElement("span");
      collabBadge.className = "collaboration-badge editing";
      collabBadge.innerHTML = `<i class="fas fa-users"></i> Live`;
      badgesContainer.appendChild(collabBadge);
    }
  }

  // ------------------------------------------------- remote cursor rendering

  /**
   * Update (or create) a remote cursor overlay for a given user.
   * Called when a cursor_update message arrives from the WebSocket.
   */
  updateRemoteCursor(
    userId: number,
    username: string,
    section: string,
    position: CursorPosition,
  ): void {
    const textarea = document.getElementById(
      `section-${section}`,
    ) as HTMLTextAreaElement | null;
    if (!textarea) return;

    let state = this.remoteCursors.get(userId);

    // If section changed, remove old overlay first
    if (state && state.section !== section) {
      state.element.remove();
      state.labelElement.remove();
      this.remoteCursors.delete(userId);
      state = undefined;
    }

    if (!state) {
      state = this.createCursorOverlay(userId, username, section);
      this.remoteCursors.set(userId, state);
    }

    state.position = position;
    state.section = section;
    this.positionCursorOverlay(state, textarea);
  }

  /** Remove cursor overlay when a user leaves. */
  removeRemoteCursor(userId: number): void {
    const state = this.remoteCursors.get(userId);
    if (state) {
      state.element.remove();
      state.labelElement.remove();
      this.remoteCursors.delete(userId);
    }
  }

  /** Remove all remote cursor overlays (e.g. on disconnect). */
  removeAllCursors(): void {
    this.remoteCursors.forEach((state) => {
      state.element.remove();
      state.labelElement.remove();
    });
    this.remoteCursors.clear();
  }

  // -------------------------------------------------- overlay DOM helpers

  private createCursorOverlay(
    _userId: number,
    username: string,
    section: string,
  ): RemoteCursorState {
    const color = colorForUser(username);

    // Cursor line element
    const cursor = document.createElement("div");
    cursor.className = "remote-cursor-overlay";
    cursor.style.cssText = [
      "position: absolute",
      `background: ${color}`,
      "width: 2px",
      "height: 1.2em",
      "pointer-events: none",
      "z-index: 10",
      "transition: top 0.12s ease, left 0.12s ease",
    ].join(";");

    // Username label
    const label = document.createElement("div");
    label.className = "remote-cursor-label";
    label.textContent = username;
    label.style.cssText = [
      "position: absolute",
      `background: ${color}`,
      "color: #fff",
      "font-size: 10px",
      "padding: 1px 4px",
      "border-radius: 2px",
      "pointer-events: none",
      "z-index: 11",
      "white-space: nowrap",
      "transition: top 0.12s ease, left 0.12s ease",
    ].join(";");

    // Attach to the textarea's offset parent (or body as fallback)
    const textarea = document.getElementById(`section-${section}`);
    const container = textarea?.parentElement ?? document.body;
    // Ensure container can anchor absolutely positioned children
    if (container !== document.body) {
      const containerPos = getComputedStyle(container).position;
      if (containerPos === "static") {
        container.style.position = "relative";
      }
    }
    container.appendChild(cursor);
    container.appendChild(label);

    return {
      username,
      section,
      position: { line: 0, ch: 0, offset: 0 },
      element: cursor,
      labelElement: label,
    };
  }

  /**
   * Position the cursor overlay relative to the textarea.
   * Uses a hidden measurement span to convert character offset to pixel coordinates.
   */
  private positionCursorOverlay(
    state: RemoteCursorState,
    textarea: HTMLTextAreaElement,
  ): void {
    const offset = state.position.offset ?? 0;
    const text = textarea.value.substring(0, offset);
    const lines = text.split("\n");
    const lineIndex = lines.length - 1;
    const charInLine = lines[lineIndex].length;

    // Approximate pixel position using textarea font metrics
    const style = getComputedStyle(textarea);
    const lineHeight =
      parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.2;
    const charWidth = this.measureCharWidth(textarea);

    const top =
      textarea.offsetTop +
      lineIndex * lineHeight -
      textarea.scrollTop +
      parseFloat(style.paddingTop);
    const left =
      textarea.offsetLeft +
      charInLine * charWidth +
      parseFloat(style.paddingLeft);

    state.element.style.top = `${top}px`;
    state.element.style.left = `${left}px`;
    state.element.style.height = `${lineHeight}px`;

    // Label sits just above the cursor line
    state.labelElement.style.top = `${top - 14}px`;
    state.labelElement.style.left = `${left}px`;
  }

  /** Measure average character width for a textarea using a hidden canvas. */
  private measureCharWidth(textarea: HTMLTextAreaElement): number {
    const style = getComputedStyle(textarea);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return 8; // fallback
    ctx.font = `${style.fontSize} ${style.fontFamily}`;
    return ctx.measureText("x").width;
  }
}
