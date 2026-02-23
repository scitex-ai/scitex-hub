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
  private themeObserver: MutationObserver | null = null;

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

    // Right-click shortcuts: single=1, double=2, triple=3, quadruple=4
    // Sends the digit, waits 500ms, then sends Enter
    let rightClickCount = 0;
    let rightClickTimer: ReturnType<typeof setTimeout> | null = null;
    const RIGHT_CLICK_WINDOW = 400;

    container.addEventListener("contextmenu", (e: MouseEvent) => {
      e.preventDefault();
      rightClickCount++;
      if (rightClickTimer) clearTimeout(rightClickTimer);
      rightClickTimer = setTimeout(() => {
        const count = Math.min(rightClickCount, 4);
        rightClickCount = 0;
        rightClickTimer = null;
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(String(count));
          setTimeout(() => {
            if (this.ws?.readyState === WebSocket.OPEN) this.ws.send("\r");
          }, 500);
        }
      }, RIGHT_CLICK_WINDOW);
    });

    // Listen for theme changes
    this.observeTheme();

    // Clipboard & selection support
    this.terminal.attachCustomKeyEventHandler((ev: KeyboardEvent) => {
      // Ctrl+A: select all terminal content
      if (
        ev.ctrlKey &&
        (ev.key === "a" || ev.key === "A") &&
        ev.type === "keydown"
      ) {
        this.terminal.selectAll();
        return false;
      }
      // Ctrl+C: copy selection (if text selected), else send interrupt
      if (ev.ctrlKey && (ev.key === "c" || ev.key === "C")) {
        const sel = this.terminal.getSelection();
        if (sel) {
          navigator.clipboard.writeText(sel);
          return false;
        }
        return true;
      }
      // Ctrl+V: paste from clipboard
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
      // Intercept OSC escapes before writing to terminal
      const processed = this.handleOscEscapes(data);
      if (processed) this.terminal.write(processed);
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
    const isDark =
      document.documentElement.getAttribute("data-theme") !== "light";
    return isDark
      ? {
          background: get("--terminal-bg", "#0d1117"),
          foreground: get("--terminal-fg", "#c9d1d9"),
          cursor: get("--terminal-cursor", "#58a6ff"),
        }
      : {
          background: get("--terminal-bg", "#ffffff"),
          foreground: get("--terminal-fg", "#24292f"),
          cursor: get("--terminal-cursor", "#0969da"),
        };
  }

  /** Watch for theme attribute changes on <html> and update terminal colors */
  private observeTheme(): void {
    if (this.themeObserver) return;
    this.themeObserver = new MutationObserver(() => this.updateTheme());
    this.themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
  }

  private updateTheme(): void {
    if (!this.terminal) return;
    const theme = this.getTheme();
    this.terminal.options.theme = theme;
  }

  /** Process OSC escape sequences (speech + media), return remaining data to write */
  private handleOscEscapes(data: string): string | null {
    let remaining = data;
    // TTS: \x1b]9999;speak:<base64>\x07
    remaining = this.extractOsc(remaining, "\x1b]9999;speak:", (b64) => {
      try {
        const text = atob(b64);
        const csrf =
          document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
            ?.value ??
          (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "");
        speakText(text, csrf);
      } catch {
        /* ignore */
      }
    });
    // Media: \x1b]9998;media:<base64-json>\x07
    remaining = this.extractOsc(remaining, "\x1b]9998;media:", (b64) => {
      try {
        const ref = JSON.parse(atob(b64));
        this.showMediaOverlay(ref);
      } catch {
        /* ignore */
      }
    });
    return remaining || null;
  }

  /** Extract and handle a single OSC escape, return data with escape removed */
  private extractOsc(
    data: string,
    prefix: string,
    handler: (b64: string) => void,
  ): string {
    const idx = data.indexOf(prefix);
    if (idx === -1) return data;
    const start = idx + prefix.length;
    const end = data.indexOf("\x07", start);
    if (end === -1) return data;
    handler(data.slice(start, end));
    return data.slice(0, idx) + data.slice(end + 1);
  }

  /** Show a floating media overlay above the terminal */
  private showMediaOverlay(ref: {
    type: string;
    path: string;
    url?: string;
  }): void {
    if (!this.container) return;
    const overlay = document.createElement("div");
    overlay.className = "scitex-terminal-media-overlay";
    const closeBtn = document.createElement("button");
    closeBtn.className = "scitex-terminal-media-close";
    closeBtn.innerHTML = "&times;";
    closeBtn.onclick = () => overlay.remove();
    overlay.appendChild(closeBtn);

    const url = ref.url || ref.path;
    if (ref.type === "image") {
      const img = document.createElement("img");
      img.src = url;
      img.style.maxWidth = "100%";
      img.style.maxHeight = "80%";
      overlay.appendChild(img);
    } else {
      const link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.textContent = ref.path.split("/").pop() || ref.path;
      link.style.color = "var(--color-accent-fg, #58a6ff)";
      overlay.appendChild(link);
    }

    this.container.style.position = "relative";
    this.container.appendChild(overlay);
    // Auto-dismiss after 15s
    setTimeout(() => overlay.remove(), 15000);
  }

  destroy(): void {
    this.resizeObserver?.disconnect();
    this.themeObserver?.disconnect();
    this.themeObserver = null;
    if (this.resizeTimeout) clearTimeout(this.resizeTimeout);
    this.ws?.close();
    this.ws = null;
    this.terminal?.dispose();
    this.terminal = null;
    this.fitAddon = null;
    this.connected = false;
  }
}
