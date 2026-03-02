/**
 * Cursor Tracker - Visual cursor position tracking for collaborative editing
 *
 * Displays remote users' cursor positions and selections in real-time
 */

console.log("[DEBUG] cursor-tracker.ts loaded");

interface RemoteCursor {
  userId: number;
  username: string;
  section: string;
  position: number;
  color: string;
  element?: HTMLElement;
  label?: HTMLElement;
}

export class CursorTracker {
  private cursors: Map<number, RemoteCursor> = new Map();
  private colorPalette: string[] = [
    "#FF6B6B", // Red
    "#4ECDC4", // Teal
    "#45B7D1", // Blue
    "#FFA07A", // Light Salmon
    "#98D8C8", // Mint
    "#F7DC6F", // Yellow
    "#BB8FCE", // Purple
    "#85C1E2", // Sky Blue
  ];
  private colorIndex: number = 0;

  constructor() {
    this.injectStyles();
  }

  /**
   * Update or create a remote cursor
   */
  updateCursor(userId: number, username: string, section: string, position: number): void {
    let cursor = this.cursors.get(userId);

    if (!cursor) {
      cursor = {
        userId,
        username,
        section,
        position,
        color: this.getNextColor(),
      };
      this.cursors.set(userId, cursor);
      console.log(`[CursorTracker] Created cursor for ${username} (${cursor.color})`);
    }

    cursor.section = section;
    cursor.position = position;

    this.renderCursor(cursor);
  }

  /**
   * Remove a remote cursor
   */
  removeCursor(userId: number): void {
    const cursor = this.cursors.get(userId);
    if (cursor) {
      this.destroyCursorElements(cursor);
      this.cursors.delete(userId);
      console.log(`[CursorTracker] Removed cursor for user ${userId}`);
    }
  }

  /**
   * Clear all remote cursors
   */
  clearAll(): void {
    this.cursors.forEach((cursor) => {
      this.destroyCursorElements(cursor);
    });
    this.cursors.clear();
  }

  /**
   * Render cursor in the DOM
   */
  private renderCursor(cursor: RemoteCursor): void {
    const textarea = document.getElementById(`section-${cursor.section}`) as HTMLTextAreaElement;
    if (!textarea) {
      console.warn(`[CursorTracker] Textarea not found for section: ${cursor.section}`);
      return;
    }

    // Create cursor element if it doesn't exist
    if (!cursor.element) {
      cursor.element = this.createCursorElement(cursor);
      cursor.label = this.createLabelElement(cursor);
    }

    // Position the cursor
    const coords = this.getCaretCoordinates(textarea, cursor.position);

    if (cursor.element) {
      cursor.element.style.left = `${coords.left}px`;
      cursor.element.style.top = `${coords.top}px`;
      cursor.element.style.height = `${coords.height}px`;
    }

    if (cursor.label) {
      cursor.label.style.left = `${coords.left}px`;
      cursor.label.style.top = `${coords.top - 20}px`;
    }
  }

  /**
   * Create cursor DOM element
   */
  private createCursorElement(cursor: RemoteCursor): HTMLElement {
    const element = document.createElement("div");
    element.className = "remote-cursor";
    element.style.backgroundColor = cursor.color;
    element.dataset.userId = cursor.userId.toString();

    // Append to textarea's parent container
    const textarea = document.getElementById(`section-${cursor.section}`) as HTMLTextAreaElement;
    if (textarea && textarea.parentElement) {
      // Ensure parent has position: relative
      if (getComputedStyle(textarea.parentElement).position === "static") {
        textarea.parentElement.style.position = "relative";
      }
      textarea.parentElement.appendChild(element);
    }

    return element;
  }

  /**
   * Create cursor label element
   */
  private createLabelElement(cursor: RemoteCursor): HTMLElement {
    const label = document.createElement("div");
    label.className = "remote-cursor-label";
    label.textContent = cursor.username;
    label.style.backgroundColor = cursor.color;
    label.dataset.userId = cursor.userId.toString();

    // Append to textarea's parent container
    const textarea = document.getElementById(`section-${cursor.section}`) as HTMLTextAreaElement;
    if (textarea && textarea.parentElement) {
      textarea.parentElement.appendChild(label);
    }

    return label;
  }

  /**
   * Destroy cursor DOM elements
   */
  private destroyCursorElements(cursor: RemoteCursor): void {
    if (cursor.element && cursor.element.parentElement) {
      cursor.element.parentElement.removeChild(cursor.element);
      cursor.element = undefined;
    }
    if (cursor.label && cursor.label.parentElement) {
      cursor.label.parentElement.removeChild(cursor.label);
      cursor.label = undefined;
    }
  }

  /**
   * Get next color from palette
   */
  private getNextColor(): string {
    const color = this.colorPalette[this.colorIndex];
    this.colorIndex = (this.colorIndex + 1) % this.colorPalette.length;
    return color;
  }

  /**
   * Calculate caret coordinates in textarea
   * Based on: https://github.com/component/textarea-caret-position
   */
  private getCaretCoordinates(element: HTMLTextAreaElement, position: number): {
    left: number;
    top: number;
    height: number;
  } {
    // Create a mirror div to calculate position
    const div = document.createElement("div");
    const computed = getComputedStyle(element);
    const isInput = element.nodeName === "INPUT";

    // Copy styles
    div.style.position = "absolute";
    div.style.visibility = "hidden";
    div.style.whiteSpace = "pre-wrap";
    div.style.wordWrap = "break-word";

    // Transfer box model properties
    const properties = [
      "direction",
      "boxSizing",
      "width",
      "height",
      "overflowX",
      "overflowY",
      "borderTopWidth",
      "borderRightWidth",
      "borderBottomWidth",
      "borderLeftWidth",
      "borderStyle",
      "paddingTop",
      "paddingRight",
      "paddingBottom",
      "paddingLeft",
      "fontStyle",
      "fontVariant",
      "fontWeight",
      "fontStretch",
      "fontSize",
      "fontSizeAdjust",
      "lineHeight",
      "fontFamily",
      "textAlign",
      "textTransform",
      "textIndent",
      "textDecoration",
      "letterSpacing",
      "wordSpacing",
    ];

    properties.forEach((prop) => {
      div.style[prop as any] = computed[prop as any];
    });

    div.textContent = element.value.substring(0, position);

    // Create a span for the cursor position
    const span = document.createElement("span");
    span.textContent = element.value.substring(position) || ".";
    div.appendChild(span);

    document.body.appendChild(div);

    const coordinates = {
      top: span.offsetTop + parseInt(computed.borderTopWidth),
      left: span.offsetLeft + parseInt(computed.borderLeftWidth),
      height: parseInt(computed.lineHeight) || 20,
    };

    document.body.removeChild(div);

    // Adjust for textarea's scroll position
    coordinates.top -= element.scrollTop;
    coordinates.left -= element.scrollLeft;

    return coordinates;
  }

  /**
   * Inject CSS styles for cursor display
   */
  private injectStyles(): void {
    if (document.getElementById("cursor-tracker-styles")) {
      return; // Already injected
    }

    const style = document.createElement("style");
    style.id = "cursor-tracker-styles";
    style.textContent = `
      .remote-cursor {
        position: absolute;
        width: 2px;
        background-color: #000;
        pointer-events: none;
        z-index: 1000;
        animation: cursor-blink 1s infinite;
        transition: left 0.1s ease, top 0.1s ease;
      }

      .remote-cursor-label {
        position: absolute;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 500;
        color: white;
        white-space: nowrap;
        pointer-events: none;
        z-index: 1001;
        transition: left 0.1s ease, top 0.1s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
      }

      @keyframes cursor-blink {
        0%, 49% { opacity: 1; }
        50%, 100% { opacity: 0.3; }
      }
    `;

    document.head.appendChild(style);
  }
}

// Export for global access
declare global {
  interface Window {
    CursorTracker: typeof CursorTracker;
  }
}

window.CursorTracker = CursorTracker;
