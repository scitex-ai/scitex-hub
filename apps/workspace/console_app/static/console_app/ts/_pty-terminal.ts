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
import {
  getTerminalThemeFromCSS,
  hideTerminalOverlay,
  showTerminalReconnectPrompt,
  showTerminalRestartOverlay,
} from "./_pty-ui-helpers";
import { handleSessionStateMessage } from "./_pty-session-state";

export class PTYTerminal {
  private term: any;
  private ws: WebSocket | null = null;
  private projectId: number;
  private tmuxSession: string;
  /** Model-provider id for this session (server-validated; "" = default). */
  private provider: string;
  private containerEl: HTMLElement;
  private imageContainer: HTMLElement | null = null;
  private readyPromise: Promise<void>;
  private readyResolve!: () => void;
  private readyReject!: (err: Error) => void;
  private spinnerTimer: ReturnType<typeof setInterval> | null = null;
  private sessionState: string = "unknown";
  private _reconnectAttempt: number = 0;
  private readonly _maxReconnectAttempts: number = 20;

  constructor(
    containerEl: HTMLElement,
    projectId: number,
    tmuxSession: string = "scitex-0",
    provider: string = "",
  ) {
    this.projectId = projectId;
    this.tmuxSession = tmuxSession;
    this.provider = provider;
    this.containerEl = containerEl;

    this.readyPromise = new Promise<void>((resolve, reject) => {
      this.readyResolve = resolve;
      this.readyReject = reject;
    });

    // Sequence: connect() only runs AFTER initXterm() resolves. initXterm
    // always yields (await document.fonts.ready) before `this.term` exists,
    // so an unawaited initXterm() + synchronous connect() used to hit
    // startSpinner() -> this.term.write with this.term undefined — a
    // deterministic TypeError inside the constructor that left the terminal
    // container hidden for every user. On init failure, reject readyPromise
    // so waitForReady() callers can surface a VISIBLE error state.
    this.initXterm(containerEl)
      .then(() => this.connect())
      .catch((err: unknown) => {
        const error = err instanceof Error ? err : new Error(String(err));
        console.error("[PTY] Terminal initialization failed:", error);
        this.readyReject(error);
      });
  }

  public async waitForReady(): Promise<void> {
    return this.readyPromise;
  }

  private async initXterm(containerEl: HTMLElement): Promise<void> {
    // Bounded wait for the xterm.js bundle: an unbounded poll left a
    // hidden, never-ready terminal with no signal when assets failed to
    // load. Fail loud instead so the tab manager can render the error.
    const deadline = Date.now() + 20000;
    while (!(window as any).Terminal) {
      if (Date.now() > deadline) {
        throw new Error(
          "xterm.js failed to load (window.Terminal still missing after 20s)",
        );
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    // Wait for web fonts (JetBrains Mono) to load before opening terminal.
    // xterm.js calculates character cell grid on open() — if the font isn't
    // loaded yet, the grid uses fallback font metrics causing text selection
    // offset and arrow key misbehavior.
    await document.fonts.ready;

    const Terminal = (window as any).Terminal;
    const FitAddon = (window as any).FitAddon?.FitAddon;
    const ImageAddon = (window as any).ImageAddon?.ImageAddon;

    this.term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
      theme: getTerminalThemeFromCSS(),
      allowProposedApi: true,
      scrollback: 10000,
    });

    this.term.open(containerEl);

    if (FitAddon) {
      const fitAddon = new FitAddon();
      this.term.loadAddon(fitAddon);
      fitAddon.fit();

      // Safety re-fit: if fonts load late despite await above, recalculate grid
      document.fonts.ready.then(() => {
        fitAddon.fit();
        this.sendResize();
      });

      // Secondary re-fit after short delay to catch late font rendering
      setTimeout(() => {
        if (fitAddon) {
          fitAddon.fit();
          this.sendResize();
        }
      }, 500);

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

  /** Return the xterm instance, or throw a CLEAR ordering error. Guards
   * the write paths so a future sequencing bug fails with an explicit
   * message instead of a property-read TypeError on `undefined`. */
  private requireTerm(): any {
    if (!this.term) {
      throw new Error(
        "PTYTerminal: xterm not initialized yet — connect()/write paths " +
          "must only run after initXterm() has resolved",
      );
    }
    return this.term;
  }

  private startSpinner(): void {
    const term = this.requireTerm();
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
    term.write(`\x1b[0;36m${frames[0]} Connecting...\x1b[0m`);
    this.spinnerTimer = setInterval(() => {
      i = (i + 1) % frames.length;
      term.write(`\r\x1b[0;36m${frames[i]} Connecting...\x1b[0m`);
    }, 80);
  }

  private stopSpinner(): void {
    if (this.spinnerTimer) {
      clearInterval(this.spinnerTimer);
      this.spinnerTimer = null;
      this.term.write("\r\x1b[2K");
    }
  }

  /** Delegate session-state control messages (see _pty-session-state.ts). */
  private handleSessionState(msg: any): void {
    this.sessionState = handleSessionStateMessage(msg, this.requireTerm(), {
      hideRestartOverlay: () => this.hideRestartOverlay(),
      showRestartOverlay: (reason: string) => this.showRestartOverlay(reason),
    });
  }

  /** Show a prominent restart overlay over the terminal */
  private showRestartOverlay(reason: string): void {
    showTerminalRestartOverlay(
      this.containerEl,
      reason,
      () => this.restart(),
      () =>
        document.querySelector<HTMLButtonElement>(".terminal-tab-new")?.click(),
    );
  }

  private hideRestartOverlay(): void {
    hideTerminalOverlay(this.containerEl);
  }

  private showReconnectPrompt(reason: string): void {
    showTerminalReconnectPrompt(this.containerEl, reason, () => {
      this._reconnectAttempt = 0;
      this.connect();
    });
  }

  private connect(): void {
    // connect() writes to the terminal (spinner, close/error messages) —
    // it must never run before initXterm() has created `this.term`.
    this.requireTerm();
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const providerParam = this.provider
      ? `&provider=${encodeURIComponent(this.provider)}`
      : "";
    const wsUrl = `${protocol}//${window.location.host}/ws/console/terminal/?project_id=${this.projectId}&tmux_session=${this.tmuxSession}${providerParam}`;

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

  public updateTheme(): void {
    if (!this.term) return;
    this.term.options.theme = getTerminalThemeFromCSS();
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
