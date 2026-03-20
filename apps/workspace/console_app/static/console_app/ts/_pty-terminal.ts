/**
 * Real PTY Terminal with xterm.js
 * Provides full interactive terminal with IPython, vim, etc.
 */

import {
  attachClipboardPasteHandler,
  attachFileDropHandler,
  attachKeyboardHandler,
  attachRightClickHandler,
} from "./_pty-input-handlers";
import { handleCaptureRequest } from "./_on-site-capture";
import { classifyCloseCode } from "./_close-codes";

export class PTYTerminal {
  private term: any;
  private ws: WebSocket | null = null;
  private projectId: number;
  private tmuxSession: string;
  private containerEl: HTMLElement;
  private imageContainer: HTMLElement | null = null;
  private readyPromise: Promise<void>;
  private readyResolve!: () => void;
  private spinnerTimer: ReturnType<typeof setInterval> | null = null;
  private sessionState: string = "unknown";
  private _reconnectAttempt: number = 0;
  private readonly _maxReconnectAttempts: number = 20;

  constructor(
    containerEl: HTMLElement,
    projectId: number,
    tmuxSession: string = "scitex-0",
  ) {
    this.projectId = projectId;
    this.tmuxSession = tmuxSession;
    this.containerEl = containerEl;

    this.readyPromise = new Promise<void>((resolve) => {
      this.readyResolve = resolve;
    });

    this.initXterm(containerEl);
    this.connect();
  }

  public async waitForReady(): Promise<void> {
    return this.readyPromise;
  }

  private async initXterm(containerEl: HTMLElement): Promise<void> {
    while (!(window as any).Terminal) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    const Terminal = (window as any).Terminal;
    const FitAddon = (window as any).FitAddon?.FitAddon;
    const ImageAddon = (window as any).ImageAddon?.ImageAddon;

    this.term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
      theme: this.getThemeFromCSS(),
      allowProposedApi: true,
      scrollback: 10000,
    });

    this.term.open(containerEl);

    if (FitAddon) {
      const fitAddon = new FitAddon();
      this.term.loadAddon(fitAddon);
      fitAddon.fit();

      window.addEventListener("resize", () => {
        fitAddon.fit();
        this.sendResize();
      });

      let lastW = 0;
      let lastH = 0;
      const resizeObserver = new ResizeObserver((entries) => {
        const { width, height } = entries[0].contentRect;
        if (Math.abs(width - lastW) < 2 && Math.abs(height - lastH) < 2) return;
        lastW = width;
        lastH = height;
        clearTimeout((this as any).resizeTimeout);
        (this as any).resizeTimeout = setTimeout(() => {
          fitAddon.fit();
          this.sendResize();
        }, 150);
      });
      resizeObserver.observe(containerEl);
    }

    if (ImageAddon) {
      try {
        const imageAddon = new ImageAddon();
        this.term.loadAddon(imageAddon);
      } catch {
        /* ImageAddon unavailable */
      }
    }

    // User input → WebSocket
    this.term.onData((data: string) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(data);
      }
    });

    // Attach input handlers from extracted module
    const getWs = () => this.ws;
    attachKeyboardHandler(this.term, getWs, containerEl, this.projectId);
    attachRightClickHandler(containerEl, getWs);
    attachFileDropHandler(containerEl, getWs, this.projectId);
    attachClipboardPasteHandler(containerEl, getWs, this.projectId);

    // Wire up restart button
    const restartBtn = document.getElementById("btn-terminal-restart");
    if (restartBtn) {
      restartBtn.addEventListener("click", () => this.restart());
    }

    // Wire up release resources button (shared allocation mode)
    const releaseBtn = document.getElementById("btn-release-resources");
    if (releaseBtn) {
      releaseBtn.addEventListener("click", () => this.releaseResources());
    }

    // Request notification permission for background alerts
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }

    console.log("[PTY] xterm.js initialized");
    this.readyResolve();
  }

  private startSpinner(): void {
    const frames = [
      "\u28CB",
      "\u28D9",
      "\u28F9",
      "\u28F8",
      "\u28FC",
      "\u28F4",
      "\u28E6",
      "\u28E7",
      "\u28C7",
      "\u28CF",
    ];
    let i = 0;
    this.term.write(`\x1b[0;36m${frames[0]} Connecting...\x1b[0m`);
    this.spinnerTimer = setInterval(() => {
      i = (i + 1) % frames.length;
      this.term.write(`\r\x1b[0;36m${frames[i]} Connecting...\x1b[0m`);
    }, 80);
  }

  private stopSpinner(): void {
    if (this.spinnerTimer) {
      clearInterval(this.spinnerTimer);
      this.spinnerTimer = null;
      this.term.write("\r\x1b[2K");
    }
  }

  private handleSessionState(msg: any): void {
    const state = msg.state;
    this.sessionState = state;
    console.log("[PTY] Session state:", state, msg);

    const badge = document.getElementById("terminal-session-status");

    switch (state) {
      case "allocation_starting":
        this.term.write(
          "\r\n\x1b[1;36m Preparing your computing environment...\x1b[0m\r\n",
        );
        this.updateBadge(badge, "starting", "warning");
        break;

      case "allocation_expiring": {
        const remaining = msg.remaining || 0;
        const minutes = Math.ceil(remaining / 60);
        const timeStr = minutes > 0 ? `${minutes} min` : `${remaining}s`;
        this.term.write(
          `\r\n\x1b[1;33m \u26a0 Session expires in ${timeStr}\x1b[0m\r\n`,
        );
        this.term.write(
          "\x1b[0;33m   Save your work. A new session will start automatically.\x1b[0m\r\n",
        );
        this.updateBadge(badge, `expires ${timeStr}`, "warning");
        this.notifyUser(`Terminal session expires in ${timeStr}`);
        break;
      }

      case "allocation_dead": {
        const reason = msg.reason || "Unknown reason";
        this.term.write(
          `\r\n\x1b[1;31m \u274c Session ended: ${reason}\x1b[0m\r\n`,
        );
        this.term.write(
          "\x1b[0;36m   Reconnecting automatically...\x1b[0m\r\n",
        );
        this.updateBadge(badge, "reconnecting", "warning");
        this.notifyUser(`Session ended: ${reason}. Reconnecting...`);
        break;
      }

      case "allocation_recovering":
        this.term.write(
          "\r\n\x1b[1;36m Preparing your computing environment...\x1b[0m\r\n",
        );
        this.updateBadge(badge, "reconnecting", "warning");
        break;

      case "exited":
      case "respawning":
        this.term.write("\r\n\x1b[1;33m Restarting terminal...\x1b[0m\r\n");
        this.updateBadge(badge, "restarting", "warning");
        break;

      case "running":
        this.hideRestartOverlay();
        this.updateBadge(badge, "", "");
        break;

      case "dead": {
        const deadReason = msg.reason || "Terminal stopped";
        this.term.write(`\r\n\x1b[1;31m \u274c ${deadReason}\x1b[0m\r\n`);
        this.updateBadge(badge, "stopped", "error");
        this.notifyUser(deadReason);
        this.showRestartOverlay(deadReason);
        break;
      }
    }
  }

  /** Update the status badge text and style */
  private updateBadge(
    badge: HTMLElement | null,
    text: string,
    level: string,
  ): void {
    if (!badge) return;
    badge.textContent = text;
    badge.className = level
      ? `terminal-status-badge status-${level}`
      : "terminal-status-badge";
  }

  /** Show/hide a prominent restart overlay over the terminal */
  private showRestartOverlay(reason: string): void {
    this.hideRestartOverlay();
    const overlay = document.createElement("div");
    overlay.className = "terminal-restart-overlay";
    overlay.innerHTML =
      `<div class="terminal-restart-content">` +
      `<i class="fas fa-exclamation-triangle"></i>` +
      `<p>${reason}</p>` +
      `<button class="terminal-restart-btn"><i class="fas fa-redo"></i> Restart Terminal</button>` +
      `<button class="terminal-new-btn"><i class="fas fa-plus"></i> New Terminal</button>` +
      `</div>`;
    overlay
      .querySelector(".terminal-restart-btn")
      ?.addEventListener("click", () => {
        this.hideRestartOverlay();
        this.restart();
      });
    overlay
      .querySelector(".terminal-new-btn")
      ?.addEventListener("click", () => {
        this.hideRestartOverlay();
        document.querySelector<HTMLButtonElement>(".terminal-tab-new")?.click();
      });
    this.containerEl.style.position = "relative";
    this.containerEl.appendChild(overlay);
  }

  private hideRestartOverlay(): void {
    this.containerEl.querySelector(".terminal-restart-overlay")?.remove();
  }

  private showReconnectPrompt(reason: string): void {
    this.hideRestartOverlay();
    const overlay = document.createElement("div");
    overlay.className = "terminal-restart-overlay";
    overlay.innerHTML =
      `<div class="terminal-restart-content">` +
      `<i class="fas fa-plug"></i>` +
      `<p>${reason}</p>` +
      `<button class="terminal-reconnect-btn">` +
      `<i class="fas fa-wifi"></i> Click to Reconnect</button></div>`;
    overlay
      .querySelector(".terminal-reconnect-btn")
      ?.addEventListener("click", () => {
        this._reconnectAttempt = 0;
        this.hideRestartOverlay();
        this.connect();
      });
    this.containerEl.style.position = "relative";
    this.containerEl.appendChild(overlay);
  }

  /** Send browser notification for background tab awareness */
  private notifyUser(message: string): void {
    if (
      document.hidden &&
      "Notification" in window &&
      Notification.permission === "granted"
    ) {
      new Notification("SciTeX Terminal", { body: message });
    }
  }

  private connect(): void {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/console/terminal/?project_id=${this.projectId}&tmux_session=${this.tmuxSession}`;

    console.log("[PTY] Connecting to:", wsUrl);
    this.startSpinner();

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.stopSpinner();
      console.log("[PTY] WebSocket connected");
      this._reconnectAttempt = 0;
      this.sendResize();
    };

    this.ws.onmessage = (event) => {
      const data = event.data;
      // Control messages use custom OSC escape: \x1b]9997;{json}\x07
      if (typeof data === "string") {
        const oscMatch = data.match(/\x1b\]9997;(.*?)\x07/);
        if (oscMatch) {
          try {
            const msg = JSON.parse(oscMatch[1]);
            if (msg.action === "session_state") {
              this.handleSessionState(msg);
              return;
            }
            if (msg.action === "capture_request") {
              handleCaptureRequest(msg);
              return;
            }
          } catch {
            // Not valid control message — fall through to terminal
          }
        }
      }
      this.term.write(data);
    };

    this.ws.onerror = (error) => {
      this.stopSpinner();
      console.error("[PTY] WebSocket error:", error);
      this.term.write("\r\n\x1b[1;31m Terminal connection error\x1b[0m\r\n");
      this.term.write(
        "\x1b[0;33m   Check network connection and try refreshing the page\x1b[0m\r\n",
      );
    };

    this.ws.onclose = (event: CloseEvent) => {
      this.stopSpinner();
      console.log("[PTY] WebSocket closed:", event.code, event.reason);

      const { message, reconnect } = classifyCloseCode(event);
      this.term.write(`\r\n\x1b[1;33m Disconnected: ${message}\x1b[0m\r\n`);

      if (reconnect) {
        if (this._reconnectAttempt >= this._maxReconnectAttempts) {
          this.term.write(
            "\x1b[0;33m   Auto-reconnect limit reached.\x1b[0m\r\n",
          );
          this.showReconnectPrompt(`Disconnected: ${message}`);
        } else {
          const delay = Math.min(
            3000 * Math.pow(2, this._reconnectAttempt),
            60000,
          );
          const delaySec = Math.round(delay / 1000);
          this.term.write(
            `\x1b[0;36m   Reconnecting in ${delaySec}s (attempt ${this._reconnectAttempt + 1}/${this._maxReconnectAttempts})...\x1b[0m\r\n`,
          );
          this._reconnectAttempt++;
          setTimeout(() => this.connect(), delay);
        }
      } else {
        this.showRestartOverlay(`Disconnected: ${message}`);
      }
    };
  }

  public restart(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log("[PTY] Sending restart command");
      this.ws.send("restart:");
    } else {
      console.log("[PTY] WebSocket not connected, reconnecting...");
      this.connect();
    }
  }

  public releaseResources(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log("[PTY] Sending stop_allocation command");
      this.ws.send("stop_allocation:");
    }
  }

  private sendResize(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.term) {
      this.ws.send(`resize:${this.term.rows}:${this.term.cols}`);
    }
  }

  public write(text: string): void {
    if (this.term) this.term.write(text);
  }

  public writeln(text: string): void {
    if (this.term) this.term.writeln(text);
  }

  public clear(): void {
    if (this.term) this.term.clear();
    if (this.imageContainer) {
      this.imageContainer.innerHTML = "";
      this.imageContainer.style.display = "none";
    }
  }

  private getThemeFromCSS(): any {
    const style = getComputedStyle(document.documentElement);
    const g = (name: string) => style.getPropertyValue(name).trim();
    return {
      background: g("--terminal-bg"),
      foreground: g("--terminal-fg"),
      cursor: g("--terminal-cursor"),
      cursorAccent: g("--terminal-cursor-accent"),
      black: g("--terminal-black"),
      red: g("--terminal-red"),
      green: g("--terminal-green"),
      yellow: g("--terminal-yellow"),
      blue: g("--terminal-blue"),
      magenta: g("--terminal-magenta"),
      cyan: g("--terminal-cyan"),
      white: g("--terminal-white"),
      brightBlack: g("--terminal-bright-black"),
      brightRed: g("--terminal-bright-red"),
      brightGreen: g("--terminal-bright-green"),
      brightYellow: g("--terminal-bright-yellow"),
      brightBlue: g("--terminal-bright-blue"),
      brightMagenta: g("--terminal-bright-magenta"),
      brightCyan: g("--terminal-bright-cyan"),
      brightWhite: g("--terminal-bright-white"),
    };
  }

  public updateTheme(): void {
    if (!this.term) return;
    this.term.options.theme = this.getThemeFromCSS();
  }

  public executeCommand(command: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(command + "\r");
    }
  }

  public destroy(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.term) this.term.dispose();
  }

  public focus(): void {
    if (this.term) this.term.focus();
  }

  public copyBuffer(): void {
    if (!this.term) return;
    const buffer = this.term.buffer.active;
    let text = "";
    for (let i = 0; i < buffer.length; i++) {
      const line = buffer.getLine(i);
      if (line) text += line.translateToString(true) + "\n";
    }
    text = text.trimEnd() + "\n";
    navigator.clipboard.writeText(text).catch((err) => {
      console.error("[PTY] Failed to copy terminal buffer:", err);
    });
  }
}
