/**
 * AI Panel Console Mode
 * Lazy-loads xterm.js and connects to the terminal WebSocket broker.
 * Provides an embedded CLI terminal for running Claude Code, Gemini CLI, Codex.
 */

import { speakText } from "./speech";

const XTERM_JS_URL = "https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js";
const XTERM_CSS_URL = "https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css";
const FIT_ADDON_URL =
  "https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js";

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const el = document.createElement("script");
    el.src = src;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(el);
  });
}

function loadCSS(href: string): void {
  if (document.querySelector(`link[href="${href}"]`)) return;
  const el = document.createElement("link");
  el.rel = "stylesheet";
  el.href = href;
  document.head.appendChild(el);
}

export class AIPanelConsoleMode {
  private terminal: any = null;
  private fitAddon: any = null;
  private ws: WebSocket | null = null;
  private container: HTMLElement | null = null;
  private statusEl: HTMLElement | null = null;
  private loaded = false;
  private connected = false;
  private resizeObserver: ResizeObserver | null = null;
  private resizeTimeout: ReturnType<typeof setTimeout> | null = null;

  async init(
    container: HTMLElement,
    statusEl: HTMLElement | null,
  ): Promise<void> {
    this.container = container;
    this.statusEl = statusEl;

    if (!this.loaded) {
      loadCSS(XTERM_CSS_URL);
      await loadScript(XTERM_JS_URL);
      await loadScript(FIT_ADDON_URL);
      this.loaded = true;
    }

    if (this.terminal) return; // already initialized

    const xterm = (window as any).Terminal;
    const Terminal = typeof xterm === "function" ? xterm : xterm?.Terminal;
    if (!Terminal) {
      console.error("[AIPanelConsole] xterm.js Terminal class not available");
      return;
    }
    const FitAddon = (window as any).FitAddon?.FitAddon;

    this.terminal = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
      theme: this.getTheme(),
    });

    this.terminal.open(container);

    if (FitAddon) {
      this.fitAddon = new FitAddon();
      this.terminal.loadAddon(this.fitAddon);
      this.fit();

      this.resizeObserver = new ResizeObserver(() => {
        if (this.resizeTimeout) clearTimeout(this.resizeTimeout);
        this.resizeTimeout = setTimeout(() => this.fit(), 100);
      });
      this.resizeObserver.observe(container);
    }

    // Forward user input to WebSocket
    this.terminal.onData((data: string) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(data);
      }
    });

    // Clipboard support
    this.terminal.attachCustomKeyEventHandler((ev: KeyboardEvent) => {
      if (ev.ctrlKey && (ev.key === "c" || ev.key === "C")) {
        const sel = this.terminal.getSelection();
        if (sel) {
          navigator.clipboard.writeText(sel);
          return false;
        }
        return true;
      }
      if (ev.ctrlKey && (ev.key === "v" || ev.key === "V")) {
        navigator.clipboard.readText().then((t: string) => {
          if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(t);
        });
        return false;
      }
      // Let Alt+A pass through to toggle panel
      if (ev.altKey && ev.key === "a") return false;
      return true;
    });

    this.connect();
  }

  private connect(): void {
    if (this.connected || !this.terminal) return;
    this.setStatus("connecting");

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    // Use project_id=0 for AI panel terminal (home project)
    const url = `${proto}//${window.location.host}/ws/console/terminal/?project_id=0`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.connected = true;
      this.setStatus("connected");
      this.sendResize();
    };

    this.ws.onmessage = (ev) => {
      const data: string = ev.data;
      // Intercept TTS speech OSC escape: \x1b]9999;speak:<base64>\x07
      const speechPrefix = "\x1b]9999;speak:";
      const idx = data.indexOf(speechPrefix);
      if (idx !== -1) {
        // Write any data before the escape to terminal
        if (idx > 0) this.terminal.write(data.slice(0, idx));
        // Extract base64 text between prefix and BEL (\x07)
        const start = idx + speechPrefix.length;
        const end = data.indexOf("\x07", start);
        if (end !== -1) {
          try {
            const text = atob(data.slice(start, end));
            const csrf =
              document.querySelector<HTMLInputElement>(
                "[name=csrfmiddlewaretoken]",
              )?.value ??
              (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "");
            speakText(text, csrf);
          } catch {
            /* ignore decode errors */
          }
          // Write any data after the escape to terminal
          const after = end + 1;
          if (after < data.length) this.terminal.write(data.slice(after));
        } else {
          // Malformed escape — write everything to terminal
          this.terminal.write(data);
        }
      } else {
        this.terminal.write(data);
      }
    };

    this.ws.onerror = () => {
      this.setStatus("error");
    };

    this.ws.onclose = (ev) => {
      this.connected = false;
      if (ev.code === 1000) {
        this.setStatus("disconnected");
      } else {
        this.setStatus("error");
        // Auto-reconnect after 3s for non-normal closes
        setTimeout(() => this.connect(), 3000);
      }
    };
  }

  private setStatus(
    state: "connecting" | "connected" | "disconnected" | "error",
  ): void {
    if (!this.statusEl) return;
    this.statusEl.classList.remove("connected");
    const icon = this.statusEl.querySelector("i");
    switch (state) {
      case "connecting":
        if (icon) icon.className = "fas fa-circle-notch fa-spin";
        this.statusEl.lastChild!.textContent = " Connecting...";
        break;
      case "connected":
        this.statusEl.classList.add("connected");
        if (icon) icon.className = "fas fa-circle";
        this.statusEl.lastChild!.textContent = " Connected";
        break;
      case "disconnected":
        if (icon) icon.className = "fas fa-circle";
        this.statusEl.lastChild!.textContent = " Disconnected";
        break;
      case "error":
        if (icon) icon.className = "fas fa-exclamation-circle";
        this.statusEl.lastChild!.textContent = " Connection failed";
        break;
    }
  }

  fit(): void {
    if (this.fitAddon) {
      try {
        this.fitAddon.fit();
        this.sendResize();
      } catch {
        /* container may be hidden */
      }
    }
  }

  private sendResize(): void {
    if (this.ws?.readyState === WebSocket.OPEN && this.terminal) {
      this.ws.send(`resize:${this.terminal.rows}:${this.terminal.cols}`);
    }
  }

  focus(): void {
    this.terminal?.focus();
  }

  private getTheme(): Record<string, string> {
    const s = getComputedStyle(document.documentElement);
    const get = (v: string, fb: string) => s.getPropertyValue(v).trim() || fb;
    return {
      background: get("--terminal-bg", "#0d1117"),
      foreground: get("--terminal-fg", "#c9d1d9"),
      cursor: get("--terminal-cursor", "#58a6ff"),
    };
  }

  destroy(): void {
    this.resizeObserver?.disconnect();
    if (this.resizeTimeout) clearTimeout(this.resizeTimeout);
    this.ws?.close();
    this.ws = null;
    this.terminal?.dispose();
    this.terminal = null;
    this.fitAddon = null;
    this.connected = false;
  }
}
