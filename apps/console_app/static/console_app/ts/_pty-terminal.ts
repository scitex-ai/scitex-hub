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

export class PTYTerminal {
  private term: any;
  private ws: WebSocket | null = null;
  private projectId: number;
  private tmuxSession: string;
  private imageContainer: HTMLElement | null = null;
  private readyPromise: Promise<void>;
  private readyResolve!: () => void;
  private spinnerTimer: ReturnType<typeof setInterval> | null = null;
  private sessionState: string = "unknown";

  constructor(
    containerEl: HTMLElement,
    projectId: number,
    tmuxSession: string = "scitex-0",
  ) {
    this.projectId = projectId;
    this.tmuxSession = tmuxSession;

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

      const resizeObserver = new ResizeObserver(() => {
        clearTimeout((this as any).resizeTimeout);
        (this as any).resizeTimeout = setTimeout(() => {
          fitAddon.fit();
          this.sendResize();
        }, 100);
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
    attachKeyboardHandler(this.term, getWs);
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
    console.log("[PTY] Session state:", state);

    const badge = document.getElementById("terminal-session-status");

    switch (state) {
      case "allocation_starting":
        this.term.write(
          "\r\n\x1b[1;36m Starting SLURM allocation...\x1b[0m\r\n",
        );
        if (badge) {
          badge.textContent = "allocating";
          badge.className = "terminal-status-badge status-warning";
        }
        break;
      case "exited":
      case "respawning":
        this.term.write("\r\n\x1b[1;33m Session restarting...\x1b[0m\r\n");
        if (badge) {
          badge.textContent = "restarting";
          badge.className = "terminal-status-badge status-warning";
        }
        break;
      case "running":
        if (badge) {
          badge.textContent = "";
          badge.className = "terminal-status-badge";
        }
        break;
      case "dead":
        this.term.write(
          "\r\n\x1b[1;31m Session failed after max retries\x1b[0m\r\n",
        );
        this.term.write(
          "\x1b[0;33m   Click restart button or refresh page\x1b[0m\r\n",
        );
        if (badge) {
          badge.textContent = "stopped";
          badge.className = "terminal-status-badge status-error";
        }
        break;
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

      const { message, reconnect } = this.classifyCloseCode(event);
      this.term.write(`\r\n\x1b[1;33m Disconnected: ${message}\x1b[0m\r\n`);

      if (reconnect) {
        this.term.write("\x1b[0;36m   Reconnecting in 3s...\x1b[0m\r\n");
        setTimeout(() => this.connect(), 3000);
      } else {
        this.term.write("\x1b[0;33m   Refresh page to reconnect\x1b[0m\r\n");
      }
    };
  }

  private classifyCloseCode(event: CloseEvent): {
    message: string;
    reconnect: boolean;
  } {
    switch (event.code) {
      case 1000:
        return {
          message: "Connection closed, reconnecting...",
          reconnect: true,
        };
      case 1001:
        return {
          message: "Server going away (maintenance or restart)",
          reconnect: true,
        };
      case 1006:
        return { message: "Connection lost (network issue)", reconnect: true };
      case 1011:
        return { message: "Server error", reconnect: true };
      case 1012:
        return { message: "Server restarting", reconnect: true };
      case 1013:
        return {
          message: "Server overloaded, try again later",
          reconnect: true,
        };
      case 4000:
        return { message: "Authentication required", reconnect: false };
      case 4001:
        return { message: "Access denied", reconnect: false };
      case 4002:
        return { message: "Project not found", reconnect: false };
      case 4003:
        return { message: "SLURM unavailable", reconnect: false };
      default:
        return {
          message: event.reason || `Connection closed (${event.code})`,
          reconnect: true,
        };
    }
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
