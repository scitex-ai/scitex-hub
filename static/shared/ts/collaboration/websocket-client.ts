/**
 * WebSocket Collaboration Client
 * Manages WebSocket connection and message handling for collaborative editing
 *
 * @version 1.0.0
 * @author SciTeX Development Team
 */

import { TextOperation } from './_ot/operations';
import { OTClient } from './_ot/client';


// ============================================================================
// Type Definitions
// ============================================================================

export interface CursorPosition {
  section: string;
  position: number;
  lineNumber: number;
  column: number;
}

export interface RemoteCursor extends CursorPosition {
  userId: number;
  username: string;
  color: string;
}

export interface Collaborator {
  userId: number;
  username: string;
  color: string;
  isActive: boolean;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

interface WebSocketHandlers {
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Error) => void;
  onUserJoined?: (collaborator: Collaborator) => void;
  onUserLeft?: (userId: number) => void;
  onCursorUpdate?: (cursor: RemoteCursor) => void;
  onSectionLocked?: (section: string, userId: number, username: string) => void;
  onSectionUnlocked?: (section: string) => void;
  onApplyOperation?: (section: string, operation: TextOperation) => void;
  onCollaboratorsUpdate?: (collaborators: Collaborator[]) => void;
}

// ============================================================================
// WebSocket Collaboration Client
// ============================================================================

export class WebSocketCollaborationClient {
  private ws: WebSocket | null = null;
  private manuscriptId: number;
  private handlers: WebSocketHandlers;

  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingInterval: ReturnType<typeof setInterval> | null = null;

  private otClients: Map<string, OTClient> = new Map();
  private collaborators: Map<number, Collaborator> = new Map();
  private isIntentionalClose: boolean = false;

  // Color palette for remote cursors
  private cursorColors: string[] = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
    '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2'
  ];
  private nextColorIndex: number = 0;

  constructor(manuscriptId: number, handlers: WebSocketHandlers = {}) {
    this.manuscriptId = manuscriptId;
    this.handlers = handlers;
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/_writer/manuscript/${this.manuscriptId}/`;

    console.log(`[WS] Connecting to ${wsUrl}`);
    this.isIntentionalClose = false;

    try {
      this.ws = new WebSocket(wsUrl);
      this.setupWebSocketHandlers();
    } catch (error) {
      console.error('[WS] Connection error:', error);
      this.handleError(error as Error);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    console.log('[WS] Intentional disconnect');
    this.isIntentionalClose = true;

    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupWebSocketHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('[WS] Connected successfully');
      this.reconnectAttempts = 0;
      this.startPing();
      this.handleConnected();
    };

    this.ws.onclose = (event) => {
      console.log(`[WS] Connection closed (console: ${event.code})`);
      this.stopPing();
      this.handleDisconnected();

      if (!this.isIntentionalClose) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (event) => {
      console.error('[WS] WebSocket error:', event);
      this.handleError(new Error('WebSocket connection error'));
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        this.handleMessage(message);
      } catch (error) {
        console.error('[WS] Failed to parse message:', error);
      }
    };
  }

  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(message: WebSocketMessage): void {
    console.log('[WS] Received:', message.type, message);

    switch (message.type) {
      case 'user_joined':
        this.handleUserJoined(message);
        break;

      case 'user_left':
        this.handleUserLeft(message);
        break;

      case 'text_change':
        this.handleTextChange(message);
        break;

      case 'operation_ack':
        this.handleOperationAck(message);
        break;

      case 'cursor_position':
        this.handleCursorPosition(message);
        break;

      case 'section_locked':
        this.handleSectionLocked(message);
        break;

      case 'section_unlocked':
        this.handleSectionUnlocked(message);
        break;

      case 'collaborators_list':
        this.handleCollaboratorsList(message);
        break;

      case 'error':
        console.error('[WS] Server error:', message.message);
        break;

      default:
        console.warn('[WS] Unknown message type:', message.type);
    }
  }

  /**
   * Send a message to server
   */
  private send(message: WebSocketMessage): void {
    if (!this.isConnected()) {
      console.error('[WS] Cannot send message: not connected');
      return;
    }

    try {
      this.ws!.send(JSON.stringify(message));
      console.log('[WS] Sent:', message.type, message);
    } catch (error) {
      console.error('[WS] Failed to send message:', error);
    }
  }

  // ========================================================================
  // OT Client Management
  // ========================================================================

  /**
   * Get or create OT client for a section
   */
  getOTClient(section: string, revision: number = 0): OTClient {
    if (!this.otClients.has(section)) {
      const client = new OTClient(
        revision,
        (operation: TextOperation) => this.sendOperation(section, operation),
        (operation: TextOperation) => this.applyRemoteOperation(section, operation)
      );
      this.otClients.set(section, client);
    }
    return this.otClients.get(section)!;
  }

  /**
   * Apply local operation (from user edit)
   */
  applyLocalOperation(section: string, operation: TextOperation): void {
    const client = this.getOTClient(section);
    client.applyClient(operation);
  }

  /**
   * Send operation to server
   */
  private sendOperation(section: string, operation: TextOperation): void {
    const client = this.getOTClient(section);
    this.send({
      type: 'text_change',
      section_id: section,
      operation: operation.toJSON(),
      version: client.getRevision()
    });
  }

  /**
   * Apply remote operation to editor
   */
  private applyRemoteOperation(section: string, operation: TextOperation): void {
    if (this.handlers.onApplyOperation) {
      this.handlers.onApplyOperation(section, operation);
    }
  }

  // ========================================================================
  // Message Handlers
  // ========================================================================

  private handleUserJoined(message: WebSocketMessage): void {
    const color = this.getNextColor();
    const collaborator: Collaborator = {
      userId: message.user_id,
      username: message.username,
      color: color,
      isActive: true
    };

    this.collaborators.set(message.user_id, collaborator);

    if (this.handlers.onUserJoined) {
      this.handlers.onUserJoined(collaborator);
    }
  }

  private handleUserLeft(message: WebSocketMessage): void {
    this.collaborators.delete(message.user_id);

    if (this.handlers.onUserLeft) {
      this.handlers.onUserLeft(message.user_id);
    }
  }

  private handleTextChange(message: WebSocketMessage): void {
    const section = message.section_id;
    const operation = TextOperation.fromJSON(message.operation);
    const client = this.getOTClient(section, message.version);

    client.applyServer(operation);
  }

  private handleOperationAck(message: WebSocketMessage): void {
    const section = message.section_id;
    const client = this.getOTClient(section);

    client.serverAck();
  }

  private handleCursorPosition(message: WebSocketMessage): void {
    const collaborator = this.collaborators.get(message.user_id);

    const cursor: RemoteCursor = {
      userId: message.user_id,
      username: message.username,
      section: message.section,
      position: message.position,
      lineNumber: message.line_number,
      column: message.column,
      color: collaborator?.color || this.getNextColor()
    };

    if (this.handlers.onCursorUpdate) {
      this.handlers.onCursorUpdate(cursor);
    }
  }

  private handleSectionLocked(message: WebSocketMessage): void {
    if (this.handlers.onSectionLocked) {
      this.handlers.onSectionLocked(message.section, message.user_id, message.username);
    }
  }

  private handleSectionUnlocked(message: WebSocketMessage): void {
    if (this.handlers.onSectionUnlocked) {
      this.handlers.onSectionUnlocked(message.section);
    }
  }

  private handleCollaboratorsList(message: WebSocketMessage): void {
    const collaborators = message.collaborators.map((c: any): Collaborator => {
      const existing = this.collaborators.get(c.user_id);
      const color = existing?.color || this.getNextColor();

      const collaborator: Collaborator = {
        userId: c.user_id,
        username: c.username,
        color: color,
        isActive: c.is_active || true
      };

      this.collaborators.set(c.user_id, collaborator);
      return collaborator;
    });

    if (this.handlers.onCollaboratorsUpdate) {
      this.handlers.onCollaboratorsUpdate(collaborators);
    }
  }

  // ========================================================================
  // Public API Methods
  // ========================================================================

  /**
   * Send cursor position update
   */
  sendCursorPosition(cursor: CursorPosition): void {
    this.send({
      type: 'cursor_position',
      section: cursor.section,
      position: cursor.position,
      line_number: cursor.lineNumber,
      column: cursor.column
    });
  }

  /**
   * Lock a section for editing
   */
  lockSection(section: string): void {
    this.send({
      type: 'section_lock',
      section: section
    });
  }

  /**
   * Unlock a section
   */
  unlockSection(section: string): void {
    this.send({
      type: 'section_unlock',
      section: section
    });
  }

  /**
   * Get all active collaborators
   */
  getCollaborators(): Collaborator[] {
    return Array.from(this.collaborators.values());
  }

  /**
   * Get OT client status for debugging
   */
  getOTStatus(section: string): any {
    const client = this.otClients.get(section);
    return client ? client.getDebugInfo() : null;
  }

  // ========================================================================
  // Connection Management
  // ========================================================================

  private handleConnected(): void {
    if (this.handlers.onConnected) {
      this.handlers.onConnected();
    }
  }

  private handleDisconnected(): void {
    if (this.handlers.onDisconnected) {
      this.handlers.onDisconnected();
    }
  }

  private handleError(error: Error): void {
    if (this.handlers.onError) {
      this.handlers.onError(error);
    }
  }

  private scheduleReconnect(): void {
    if (this.isIntentionalClose) {
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnection attempts reached');
      this.handleError(new Error('Failed to reconnect after multiple attempts'));
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private startPing(): void {
    // Send ping every 30 seconds to keep connection alive
    this.pingInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: 'ping' });
      }
    }, 30000);
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  // ========================================================================
  // Utility Methods
  // ========================================================================

  private getNextColor(): string {
    const color = this.cursorColors[this.nextColorIndex];
    this.nextColorIndex = (this.nextColorIndex + 1) % this.cursorColors.length;
    return color;
  }
}
