/**
 * WebSocket Client for Writer Real-Time Collaboration
 *
 * Connects to ws/writer/manuscript/<id>/ and dispatches server events
 * to registered callbacks. Handles reconnection with exponential backoff.
 *
 * @version 1.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

import type { CursorPosition, ServerMessage, WSEventCallbacks } from "./types";

const LOG_PREFIX = "[WriterWS]";

/** Configuration for reconnection behaviour. */
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const CURSOR_THROTTLE_MS = 100;

export class WriterWSClient {
  private ws: WebSocket | null = null;
  private manuscriptId: number;
  private callbacks: WSEventCallbacks = {};
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private disposed = false;
  private lastCursorSend = 0;

  constructor(manuscriptId: number) {
    this.manuscriptId = manuscriptId;
  }

  // ------------------------------------------------------------------ public

  /** Register event callbacks. Can be called before or after connect(). */
  subscribe(callbacks: WSEventCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /** Open the WebSocket connection. */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.warn(LOG_PREFIX, "Already connected");
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/writer/manuscript/${this.manuscriptId}/`;
    console.log(LOG_PREFIX, "Connecting to", url);

    this.ws = new WebSocket(url);
    this.ws.onopen = this.handleOpen.bind(this);
    this.ws.onclose = this.handleClose.bind(this);
    this.ws.onerror = this.handleError.bind(this);
    this.ws.onmessage = this.handleMessage.bind(this);
  }

  /** Gracefully close the connection (no reconnect). */
  disconnect(): void {
    this.disposed = true;
    this.clearReconnectTimer();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /** Whether the socket is currently open. */
  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  // ------------------------------------------------------- outbound messages

  /** Send a cursor position update (throttled). */
  sendCursorPosition(section: string, position: CursorPosition): void {
    const now = Date.now();
    if (now - this.lastCursorSend < CURSOR_THROTTLE_MS) return;
    this.lastCursorSend = now;
    this.send({ type: "cursor_position", section, position });
  }

  /** Send a text change operation. */
  sendTextChange(sectionId: string, operation: unknown, version: number): void {
    this.send({
      type: "text_change",
      section_id: sectionId,
      operation,
      version,
    });
  }

  /** Request to lock a section. */
  sendSectionLock(section: string): void {
    this.send({ type: "section_lock", section });
  }

  /** Request to unlock a section. */
  sendSectionUnlock(section: string): void {
    this.send({ type: "section_unlock", section });
  }

  /** Request undo for a section. */
  sendUndo(sectionId: string, version: number): void {
    this.send({ type: "undo", section_id: sectionId, version });
  }

  /** Request redo for a section. */
  sendRedo(sectionId: string, version: number): void {
    this.send({ type: "redo", section_id: sectionId, version });
  }

  /** Acknowledge a received operation. */
  sendOperationAck(operationId: string, sectionId: string): void {
    this.send({
      type: "operation_ack",
      operation_id: operationId,
      section_id: sectionId,
    });
  }

  // --------------------------------------------------- internal send helper

  private send(data: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn(LOG_PREFIX, "Cannot send, socket not open");
      return;
    }
    this.ws.send(JSON.stringify(data));
  }

  // --------------------------------------------------- connection lifecycle

  private handleOpen(): void {
    console.log(LOG_PREFIX, "Connected");
    this.reconnectAttempts = 0;
    this.callbacks.onConnectionChange?.(true);
  }

  private handleClose(event: CloseEvent): void {
    console.log(LOG_PREFIX, "Disconnected", event.code, event.reason);
    this.ws = null;
    this.callbacks.onConnectionChange?.(false);

    if (!this.disposed) {
      this.scheduleReconnect();
    }
  }

  private handleError(event: Event): void {
    console.error(LOG_PREFIX, "WebSocket error", event);
  }

  // --------------------------------------------------------- message router

  private handleMessage(event: MessageEvent): void {
    let data: ServerMessage;
    try {
      data = JSON.parse(event.data) as ServerMessage;
    } catch {
      console.error(LOG_PREFIX, "Failed to parse message", event.data);
      return;
    }

    switch (data.type) {
      case "collaborators_list":
        this.callbacks.onCollaboratorsList?.(data.collaborators);
        break;

      case "user_joined":
        this.callbacks.onUserJoined?.(data.user_id, data.username);
        break;

      case "user_left":
        this.callbacks.onUserLeft?.(data.user_id, data.username);
        break;

      case "cursor_update":
        this.callbacks.onCursorUpdate?.(
          data.user_id,
          data.username,
          data.section,
          data.position,
        );
        break;

      case "section_locked":
        this.callbacks.onSectionLocked?.(
          data.user_id,
          data.username,
          data.section,
        );
        break;

      case "section_unlocked":
        this.callbacks.onSectionUnlocked?.(
          data.user_id,
          data.username,
          data.section,
        );
        break;

      case "text_change":
        this.callbacks.onTextChange?.(
          data.user_id,
          data.section,
          data.section_id,
          data.operation,
        );
        break;

      case "operation_submitted":
        this.callbacks.onOperationSubmitted?.(
          data.operation_id,
          data.status,
          data.current_version,
        );
        break;

      case "operation_error":
        this.callbacks.onOperationError?.(data.operation_id, data.error);
        break;

      case "lock_failed":
        this.callbacks.onLockFailed?.(data.section, data.message);
        break;

      case "error":
        console.error(LOG_PREFIX, "Server error:", data.message);
        break;

      default:
        console.log(
          LOG_PREFIX,
          "Unhandled message type:",
          (data as { type: string }).type,
        );
    }
  }

  // ------------------------------------------------------------ reconnection

  private scheduleReconnect(): void {
    this.clearReconnectTimer();
    const delay = Math.min(
      RECONNECT_BASE_MS * Math.pow(2, this.reconnectAttempts),
      RECONNECT_MAX_MS,
    );
    this.reconnectAttempts++;
    console.log(
      LOG_PREFIX,
      `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`,
    );
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
