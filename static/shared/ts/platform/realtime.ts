/**
 * Platform Realtime — WebSocket client for user apps.
 *
 * Connects to the PlatformRealtimeConsumer on the backend.
 * Provides broadcast, presence, and messaging APIs.
 *
 * Usage:
 *   import { PlatformRealtime } from "platform/realtime";
 *   const channel = PlatformRealtime.connect("writer", "editing", docId);
 *   channel.on("message", (data) => { ... });
 *   channel.send({ type: "cursor", line: 42 });
 */

type MessageHandler = (data: Record<string, unknown>) => void;

interface RealtimeChannel {
  send(data: Record<string, unknown>): void;
  on(event: string, handler: MessageHandler): void;
  off(event: string, handler: MessageHandler): void;
  close(): void;
  readonly readyState: number;
}

class PlatformRealtimeChannel implements RealtimeChannel {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnects = 5;

  constructor(
    private app: string,
    private channel: string,
    private resourceId: string,
  ) {
    this.connect();
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  private connect(): void {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/platform/realtime/${this.app}/${this.channel}/${this.resourceId}/`;
    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const eventType = (data.type as string) || "message";
      const handlers = this.handlers.get(eventType);
      if (handlers) {
        handlers.forEach((h) => h(data));
      }
      // Also fire "message" for all events
      if (eventType !== "message") {
        const allHandlers = this.handlers.get("message");
        if (allHandlers) {
          allHandlers.forEach((h) => h(data));
        }
      }
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnects) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
        setTimeout(() => this.connect(), delay);
      }
    };

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
    };
  }

  send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  on(event: string, handler: MessageHandler): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  off(event: string, handler: MessageHandler): void {
    this.handlers.get(event)?.delete(handler);
  }

  close(): void {
    this.maxReconnects = 0;
    this.ws?.close();
  }
}

/**
 * Static entry point for connecting to platform realtime channels.
 */
export const PlatformRealtime = {
  connect(app: string, channel: string, resourceId: string): RealtimeChannel {
    return new PlatformRealtimeChannel(app, channel, resourceId);
  },

  subscribe(app: string, channel: string, resourceId: string): RealtimeChannel {
    return this.connect(app, channel, resourceId);
  },

  presence(app: string, channel: string, resourceId: string): RealtimeChannel {
    return this.connect(app, `presence_${channel}`, resourceId);
  },
};
