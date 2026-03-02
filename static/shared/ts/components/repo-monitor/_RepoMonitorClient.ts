/**
 * Repository Monitor WebSocket Client
 * Manages WebSocket connection for real-time file change events
 */

import type { FsEvent, FilterConfig, EventCallback } from "./types";
import { DEFAULT_FILTER_CONFIG } from "./types";

const MAX_RETRIES = 5;
const BASE_RETRY_DELAY_MS = 1000;
const MAX_RETRY_DELAY_MS = 10000;

export class RepoMonitorClient {
  private projectId: string;
  private ws: WebSocket | null = null;
  private callbacks: EventCallback[] = [];
  private retryCount = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private isPaused = false;
  private shouldReconnect = true;

  constructor(projectId: string) {
    this.projectId = projectId;
  }

  connect(): void {
    this.shouldReconnect = true;
    this.openSocket();
  }

  private openSocket(): void {
    const url = `ws://${location.host}/ws/project/repo-monitor/?project_id=${this.projectId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("[RepoMonitorClient] Connected");
      this.retryCount = 0;
      const filters = this.loadFilters();
      this.send({ type: "configure", filters });
    };

    this.ws.onmessage = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "fs_event") {
          const event = data as FsEvent;
          this.callbacks.forEach((cb) => cb(event));
        }
      } catch (err) {
        console.warn("[RepoMonitorClient] Failed to parse message:", err);
      }
    };

    this.ws.onclose = () => {
      console.log("[RepoMonitorClient] Connection closed");
      if (this.shouldReconnect && this.retryCount < MAX_RETRIES) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (err) => {
      console.warn("[RepoMonitorClient] WebSocket error:", err);
    };
  }

  private scheduleReconnect(): void {
    const delay = Math.min(
      BASE_RETRY_DELAY_MS * Math.pow(2, this.retryCount),
      MAX_RETRY_DELAY_MS,
    );
    this.retryCount++;
    console.log(
      `[RepoMonitorClient] Reconnecting in ${delay}ms (attempt ${this.retryCount}/${MAX_RETRIES})`,
    );
    this.retryTimer = setTimeout(() => {
      this.openSocket();
    }, delay);
  }

  private send(data: object): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private loadFilters(): FilterConfig {
    try {
      const raw = localStorage.getItem("scitex-repo-monitor-filters");
      if (raw) return JSON.parse(raw) as FilterConfig;
    } catch {
      // ignore
    }
    return DEFAULT_FILTER_CONFIG;
  }

  onEvent(callback: EventCallback): void {
    this.callbacks.push(callback);
  }

  reconfigure(filters: FilterConfig): void {
    this.send({ type: "reconfigure", filters });
  }

  pause(): void {
    this.isPaused = true;
    this.send({ type: "pause" });
  }

  resume(): void {
    this.isPaused = false;
    this.send({ type: "resume" });
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.retryTimer !== null) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
