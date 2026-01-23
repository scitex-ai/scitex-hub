/**
 * Writer Collaboration Manager
 * Main coordination class for collaborative editing
 *
 * @version 1.0.0
 * @author SciTeX Development Team
 */

import { WebSocketCollaborationClient } from '../websocket-client.ts';
import { TextOperation } from '../ot/operations.ts';
import { RemoteCursorManager } from './cursors.ts';
import { CollaborationEventHandlers, updateCollaborationUI } from './events.ts';
import { monacoChangeToOTOperation, sendCurrentCursorPosition } from './sync.ts';

declare global {
  interface Window {
    WRITER_CONFIG?: {
      projectId: number;
      userId: number;
      username: string;
    };
    monacoEditors?: Map<string, any>;
  }
}

/**
 * Main collaboration manager for Writer application
 */
export class WriterCollaboration {
  private wsClient: WebSocketCollaborationClient | null = null;
  private cursorManagers: Map<string, RemoteCursorManager> = new Map();
  private isEnabled: boolean = false;

  private changeListeners: Map<string, any> = new Map();
  private cursorListeners: Map<string, any> = new Map();
  private eventHandlers: CollaborationEventHandlers | null = null;

  constructor() {
    console.log('[WriterCollab] Initializing collaboration');
  }

  /**
   * Enable collaborative editing
   */
  enable(manuscriptId: number): void {
    if (this.isEnabled) {
      console.log('[WriterCollab] Already enabled');
      return;
    }

    console.log('[WriterCollab] Enabling collaboration for manuscript:', manuscriptId);
    this.isEnabled = true;

    // Create event handlers
    this.eventHandlers = new CollaborationEventHandlers(this.cursorManagers, null);

    // Create WebSocket client
    this.wsClient = new WebSocketCollaborationClient(manuscriptId, {
      onConnected: () => this.eventHandlers!.handleConnected(),
      onDisconnected: () => this.eventHandlers!.handleDisconnected(),
      onError: (error) => this.eventHandlers!.handleError(error),
      onUserJoined: (user) => this.eventHandlers!.handleUserJoined(user),
      onUserLeft: (userId) => this.eventHandlers!.handleUserLeft(userId),
      onCursorUpdate: (cursor) => this.eventHandlers!.handleCursorUpdate(cursor),
      onSectionLocked: (section, userId, username) =>
        this.eventHandlers!.handleSectionLocked(section, userId, username),
      onSectionUnlocked: (section) => this.eventHandlers!.handleSectionUnlocked(section),
      onApplyOperation: (section, operation) => this.applyRemoteOperation(section, operation),
      onCollaboratorsUpdate: (collaborators) =>
        this.eventHandlers!.handleCollaboratorsUpdate(collaborators)
    });

    // Update event handlers with wsClient reference
    (this.eventHandlers as any).wsClient = this.wsClient;

    // Connect to server
    this.wsClient.connect();

    // Setup editor listeners
    this.setupEditorListeners();

    // Update UI
    updateCollaborationUI(true);
  }

  /**
   * Disable collaborative editing
   */
  disable(): void {
    if (!this.isEnabled) {
      return;
    }

    console.log('[WriterCollab] Disabling collaboration');
    this.isEnabled = false;

    // Disconnect WebSocket
    if (this.wsClient) {
      this.wsClient.disconnect();
      this.wsClient = null;
    }

    // Remove editor listeners
    this.removeEditorListeners();

    // Clear cursor managers
    this.cursorManagers.forEach(manager => manager.clear());
    this.cursorManagers.clear();

    // Update UI
    updateCollaborationUI(false);
  }

  /**
   * Setup Monaco editor listeners
   */
  private setupEditorListeners(): void {
    if (!window.monacoEditors) {
      console.warn('[WriterCollab] Monaco editors not initialized');
      return;
    }

    window.monacoEditors.forEach((editor, section) => {
      // Listen for content changes
      const changeListener = editor.onDidChangeModelContent((event: any) => {
        this.handleEditorChange(section, event, editor);
      });
      this.changeListeners.set(section, changeListener);

      // Listen for cursor position changes
      const cursorListener = editor.onDidChangeCursorPosition((_event: any) => {
        this.handleCursorChange(section, editor);
      });
      this.cursorListeners.set(section, cursorListener);

      // Create cursor manager for this editor
      this.cursorManagers.set(section, new RemoteCursorManager(editor));

      // Send cursor position when focusing
      editor.onDidFocusEditorText(() => {
        if (this.wsClient) {
          sendCurrentCursorPosition(section, editor, this.wsClient);
        }
      });
    });
  }

  /**
   * Remove Monaco editor listeners
   */
  private removeEditorListeners(): void {
    this.changeListeners.forEach(listener => listener.dispose());
    this.changeListeners.clear();

    this.cursorListeners.forEach(listener => listener.dispose());
    this.cursorListeners.clear();
  }

  /**
   * Handle editor content change
   */
  private handleEditorChange(section: string, event: any, editor: any): void {
    if (!this.wsClient || !this.isEnabled) {
      return;
    }

    // Convert Monaco changes to OT operations
    for (const change of event.changes) {
      const operation = monacoChangeToOTOperation(change, editor);
      if (!operation.isNoop()) {
        this.wsClient.applyLocalOperation(section, operation);
      }
    }
  }

  /**
   * Apply remote OT operation to editor
   */
  private applyRemoteOperation(section: string, operation: TextOperation): void {
    if (!window.monacoEditors) {
      return;
    }

    const editor = window.monacoEditors.get(section);
    if (!editor) {
      console.warn(`[WriterCollab] Editor not found for section: ${section}`);
      return;
    }

    const model = editor.getModel();
    const currentText = model.getValue();

    // Suppress our own change listeners while applying remote operation
    const changeListener = this.changeListeners.get(section);
    if (changeListener) {
      changeListener.dispose();
    }

    try {
      // Apply operation to text
      const newText = operation.apply(currentText);

      // Update editor
      model.setValue(newText);
    } catch (error) {
      console.error('[WriterCollab] Failed to apply remote operation:', error);
    } finally {
      // Re-enable change listener
      const newListener = editor.onDidChangeModelContent((event: any) => {
        this.handleEditorChange(section, event, editor);
      });
      this.changeListeners.set(section, newListener);
    }
  }

  /**
   * Handle cursor position change
   */
  private handleCursorChange(section: string, editor: any): void {
    if (!this.wsClient || !this.isEnabled) {
      return;
    }

    sendCurrentCursorPosition(section, editor, this.wsClient);
  }

  /**
   * Get current collaboration status
   */
  getStatus(): any {
    return {
      enabled: this.isEnabled,
      connected: this.wsClient?.isConnected() || false,
      collaborators: this.wsClient?.getCollaborators() || []
    };
  }
}
