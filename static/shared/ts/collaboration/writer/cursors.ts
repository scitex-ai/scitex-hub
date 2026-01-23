/**
 * Remote Cursor Management for Writer Collaboration
 * Handles cursor decorations and labels for remote collaborators
 *
 * @version 1.0.0
 * @author SciTeX Development Team
 */

import { RemoteCursor } from '../websocket-client.ts';

declare global {
  interface Window {
    monaco?: any;
  }
}

/**
 * Manages cursor decorations and labels for remote users in Monaco editor
 */
export class RemoteCursorManager {
  private editor: any;
  private decorations: Map<number, string[]> = new Map();
  private widgets: Map<number, any> = new Map();

  constructor(editor: any) {
    this.editor = editor;
  }

  /**
   * Update or create cursor decoration for a remote user
   */
  updateCursor(cursor: RemoteCursor): void {
    // Remove old decorations
    const oldDecorations = this.decorations.get(cursor.userId) || [];
    this.decorations.set(
      cursor.userId,
      this.editor.deltaDecorations(oldDecorations, [
        {
          range: new window.monaco.Range(
            cursor.lineNumber || 1,
            cursor.column || 1,
            cursor.lineNumber || 1,
            cursor.column || 1
          ),
          options: {
            className: `remote-cursor remote-cursor-${cursor.userId}`,
            stickiness: window.monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges
          }
        }
      ])
    );

    // Update cursor label widget
    this.updateCursorWidget(cursor);
  }

  /**
   * Update or create cursor label widget
   */
  private updateCursorWidget(cursor: RemoteCursor): void {
    // Remove old widget if exists
    const oldWidget = this.widgets.get(cursor.userId);
    if (oldWidget) {
      this.editor.removeContentWidget(oldWidget);
    }

    // Create new widget
    const widget = {
      getId: () => `remote-cursor-widget-${cursor.userId}`,
      getDomNode: () => {
        const node = document.createElement('div');
        node.className = 'remote-cursor-label';
        node.style.background = cursor.color || '#4ECDC4';
        node.style.color = '#fff';
        node.style.padding = '2px 6px';
        node.style.borderRadius = '3px';
        node.style.fontSize = '11px';
        node.style.fontWeight = 'bold';
        node.style.pointerEvents = 'none';
        node.style.zIndex = '100';
        node.textContent = cursor.username;
        return node;
      },
      getPosition: () => ({
        position: {
          lineNumber: cursor.lineNumber || 1,
          column: cursor.column || 1
        },
        preference: [
          window.monaco.editor.ContentWidgetPositionPreference.ABOVE,
          window.monaco.editor.ContentWidgetPositionPreference.BELOW
        ]
      })
    };

    this.editor.addContentWidget(widget);
    this.widgets.set(cursor.userId, widget);
  }

  /**
   * Remove cursor decoration and widget for a user
   */
  removeCursor(userId: number): void {
    // Remove decorations
    const decorations = this.decorations.get(userId) || [];
    this.editor.deltaDecorations(decorations, []);
    this.decorations.delete(userId);

    // Remove widget
    const widget = this.widgets.get(userId);
    if (widget) {
      this.editor.removeContentWidget(widget);
      this.widgets.delete(userId);
    }
  }

  /**
   * Clear all cursor decorations and widgets
   */
  clear(): void {
    this.decorations.forEach((decorations) => {
      this.editor.deltaDecorations(decorations, []);
    });
    this.decorations.clear();

    this.widgets.forEach((widget) => {
      this.editor.removeContentWidget(widget);
    });
    this.widgets.clear();
  }
}
