/**
 * CommsClient -- WebSocket client for real-time messaging.
 *
 * Follows the same pattern as PlatformRealtimeChannel
 * (static/shared/ts/platform/realtime.ts).
 *
 * Usage:
 *   import { CommsClient } from "./comms-client";
 *   const client = new CommsClient("general");
 *   client.on("message.new", (data) => { ... });
 *   client.sendMessage("hello world");
 */

import type { EventHandler, ServerEvent, ServerEventType } from "./types";

const TYPING_DEBOUNCE_MS = 3000;

export class CommsClient {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnects = 5;
  private typingTimer: ReturnType<typeof setTimeout> | null = null;
  private isTyping = false;

  constructor(private channelSlug: string) {
    this.connect();
  }

  // ------------------------------------------------------------ connection

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private connect(): void {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/comms/channel/${this.channelSlug}/`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.emit("_open", {} as ServerEvent);
    };

    this.ws.onmessage = (event: MessageEvent) => {
      let data: ServerEvent;
      try {
        data = JSON.parse(event.data);
      } catch {
        console.error("[CommsClient] Failed to parse message:", event.data);
        return;
      }
      const eventType = data.type || "message";
      this.emit(eventType, data);
    };

    this.ws.onclose = () => {
      this.emit("_close", {} as ServerEvent);
      if (this.reconnectAttempts < this.maxReconnects) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
        setTimeout(() => this.connect(), delay);
      }
    };

    this.ws.onerror = () => {
      console.error(
        "[CommsClient] WebSocket error on channel:",
        this.channelSlug,
      );
    };
  }

  // -------------------------------------------------------------- sending

  /** Send a chat message. Optionally provide a parent_id for threading. */
  sendMessage(text: string, parentId?: number): void {
    this.send({
      type: "message.send",
      text,
      parent_id: parentId ?? null,
    });
  }

  /** Edit an existing message (sender only). */
  editMessage(messageId: number, text: string): void {
    this.send({
      type: "message.edit",
      message_id: messageId,
      text,
    });
  }

  /** Signal that the user started typing (debounced). */
  startTyping(): void {
    if (!this.isTyping) {
      this.isTyping = true;
      this.send({ type: "typing.start" });
    }
    // Reset the debounce timer
    if (this.typingTimer !== null) {
      clearTimeout(this.typingTimer);
    }
    this.typingTimer = setTimeout(() => {
      this.stopTyping();
    }, TYPING_DEBOUNCE_MS);
  }

  /** Signal that the user stopped typing. */
  stopTyping(): void {
    if (this.isTyping) {
      this.isTyping = false;
      this.send({ type: "typing.stop" });
    }
    if (this.typingTimer !== null) {
      clearTimeout(this.typingTimer);
      this.typingTimer = null;
    }
  }

  /** Mark channel as read. */
  markRead(): void {
    this.send({ type: "mark_read" });
  }

  /** Low-level send. */
  private send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  // -------------------------------------------------------- event handling

  /** Subscribe to a server event type. */
  on(event: ServerEventType | string, handler: EventHandler): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  /** Unsubscribe from a server event type. */
  off(event: ServerEventType | string, handler: EventHandler): void {
    this.handlers.get(event)?.delete(handler);
  }

  private emit(event: string, data: ServerEvent): void {
    const handlers = this.handlers.get(event);
    if (handlers) {
      handlers.forEach((h) => h(data));
    }
  }

  // --------------------------------------------------------------- teardown

  /** Disconnect and stop reconnecting. */
  close(): void {
    this.maxReconnects = 0;
    this.stopTyping();
    this.ws?.close();
  }
}
