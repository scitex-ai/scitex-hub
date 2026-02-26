/**
 * Real PTY Terminal with xterm.js
 * Provides full interactive terminal with IPython, vim, etc.
 */

export class PTYTerminal {
  private term: any;
  private ws: WebSocket | null = null;
  private projectId: number;
  private tmuxSession: string;
  private imageContainer: HTMLElement | null = null;
  private readyPromise: Promise<void>;
  private readyResolve!: () => void;
  private spinnerTimer: ReturnType<typeof setInterval> | null = null;

  constructor(
    containerEl: HTMLElement,
    projectId: number,
    tmuxSession: string = "scitex-0",
  ) {
    this.projectId = projectId;
    this.tmuxSession = tmuxSession;

    // Create a promise that resolves when initialization is complete
    this.readyPromise = new Promise<void>((resolve) => {
      this.readyResolve = resolve;
    });

    this.initXterm(containerEl);
    this.connect();
  }

  /**
   * Wait for the terminal to be fully initialized
   * @returns Promise that resolves when xterm is ready
   */
  public async waitForReady(): Promise<void> {
    return this.readyPromise;
  }

  private async initXterm(containerEl: HTMLElement): Promise<void> {
    // Wait for xterm.js to load
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

    // Fit addon for auto-resize
    if (FitAddon) {
      const fitAddon = new FitAddon();
      this.term.loadAddon(fitAddon);
      fitAddon.fit();

      // Resize on window resize
      window.addEventListener("resize", () => {
        fitAddon.fit();
        this.sendResize();
      });

      // Resize when terminal container size changes (e.g., panel resizing)
      const resizeObserver = new ResizeObserver(() => {
        // Debounce to avoid excessive resizes
        clearTimeout((this as any).resizeTimeout);
        (this as any).resizeTimeout = setTimeout(() => {
          fitAddon.fit();
          this.sendResize();
        }, 100);
      });
      resizeObserver.observe(containerEl);
    }

    // Image addon for inline images (matplotlib, PIL, etc.)
    if (ImageAddon) {
      try {
        const imageAddon = new ImageAddon();
        this.term.loadAddon(imageAddon);
      } catch {
        /* ImageAddon unavailable */
      }
    }

    // Handle user input
    this.term.onData((data: string) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(data);
      }
    });

    // Add clipboard support and global navigation shortcuts
    this.term.attachCustomKeyEventHandler((event: KeyboardEvent) => {
      // Global navigation shortcuts (Alt+key) - HIGHEST PRIORITY
      if (event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
        const key = event.key.toLowerCase();
        const navigationRoutes: Record<string, string> = {
          s: "/scholar/",
          v: "/vis/",
          w: "/writer/",
        };

        // Alt+Z: Toggle Zen Mode
        if (key === "z") {
          console.log("[PTY] Alt+Z - Toggle Zen Mode");
          const zenEvent = new KeyboardEvent("keydown", {
            key: "F11",
            keyCode: 122,
            bubbles: true,
            cancelable: true,
          });
          document.dispatchEvent(zenEvent);
          return false;
        }

        // Alt+F: Toggle sidebar
        if (key === "f") {
          console.log("[PTY] Alt+F - Toggle sidebar");
          const sidebarToggle = document.getElementById("sidebar-toggle");
          if (sidebarToggle) sidebarToggle.click();
          return false;
        }

        // Module navigation (Alt+S/C/V/W)
        if (navigationRoutes[key]) {
          const route = navigationRoutes[key];
          if (!window.location.pathname.startsWith(route)) {
            console.log(
              `[PTY] Alt+${key.toUpperCase()} - Navigate to ${route}`,
            );
            window.location.href = route;
          }
          return false; // Prevent terminal from receiving this
        }
      }

      // Ctrl+C or Ctrl+Shift+C: Copy selected text (if selection exists)
      if (event.ctrlKey && (event.key === "C" || event.key === "c")) {
        const selection = this.term.getSelection();
        if (selection) {
          navigator.clipboard.writeText(selection);
          console.log(
            "[PTY] Copied to clipboard:",
            selection.substring(0, 50) + "...",
          );
          return false; // Prevent default and don't send to terminal
        }
        // If no selection, allow Ctrl+C to send SIGINT to terminal
        return true;
      }

      // Ctrl+V or Ctrl+Shift+V: Paste from clipboard
      if (event.ctrlKey && (event.key === "V" || event.key === "v")) {
        navigator.clipboard.readText().then((text) => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(text);
          }
        });
        return false; // Prevent default
      }

      return true; // Allow other keys
    });

    // Right-click shortcuts: single=1, double=2, triple=3, quadruple=4
    // Sends the digit, waits 500ms, then sends Enter
    let rightClickCount = 0;
    let rightClickTimer: ReturnType<typeof setTimeout> | null = null;
    const RIGHT_CLICK_WINDOW = 400; // ms to wait for additional clicks

    containerEl.addEventListener("contextmenu", (e: MouseEvent) => {
      e.preventDefault();
      rightClickCount++;

      if (rightClickTimer) clearTimeout(rightClickTimer);

      rightClickTimer = setTimeout(() => {
        const count = Math.min(rightClickCount, 4);
        rightClickCount = 0;
        rightClickTimer = null;

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          const digit = String(count);
          console.log(
            `[PTY] Right-click x${count} → sending "${digit}" + Enter`,
          );
          this.ws.send(digit);
          setTimeout(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
              this.ws.send("\r");
            }
          }, 500);
        }
      }, RIGHT_CLICK_WINDOW);
    });

    // File drop support — upload external OS files, type paths
    containerEl.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
      containerEl.classList.add("drop-target");
    });
    containerEl.addEventListener("dragleave", () => {
      containerEl.classList.remove("drop-target");
    });
    containerEl.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      containerEl.classList.remove("drop-target");
      const dt = e.dataTransfer;
      if (!dt) return;
      if (dt.files && dt.files.length > 0) {
        const csrf =
          document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
            ?.value ??
          (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "");
        const form = new FormData();
        for (let i = 0; i < dt.files.length; i++)
          form.append("files", dt.files[i]);
        void fetch("/llm/api/upload/", {
          method: "POST",
          headers: { "X-CSRFToken": csrf },
          body: form,
        })
          .then((r) => r.json())
          .then((d: any) => {
            if (this.ws?.readyState === WebSocket.OPEN)
              this.ws.send(d.paths.join(" "));
          })
          .catch((err) => console.error("[PTY] Upload error:", err));
        return;
      }
      const raw = dt.getData("text/plain") ?? "";
      const paths = raw.split(";").filter(Boolean);
      if (paths.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(paths.join(" "));
      }
    });

    console.log("[PTY] xterm.js initialized");

    // Signal that initialization is complete
    this.readyResolve();
  }

  private startSpinner(): void {
    const frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
    let i = 0;
    // Show initial frame
    this.term.write(`\x1b[0;36m${frames[0]} Connecting...\x1b[0m`);
    this.spinnerTimer = setInterval(() => {
      i = (i + 1) % frames.length;
      // Move to start of line, clear, redraw
      this.term.write(`\r\x1b[0;36m${frames[i]} Connecting...\x1b[0m`);
    }, 80);
  }

  private stopSpinner(): void {
    if (this.spinnerTimer) {
      clearInterval(this.spinnerTimer);
      this.spinnerTimer = null;
      // Clear the spinner line
      this.term.write("\r\x1b[2K");
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
      // Simply write all data to terminal - no inline image rendering
      this.term.write(event.data);
    };

    this.ws.onerror = (error) => {
      this.stopSpinner();
      console.error("[PTY] WebSocket error:", error);
      this.term.write("\r\n\x1b[1;31m❌ Terminal connection error\x1b[0m\r\n");
      this.term.write(
        "\x1b[0;33m   Check network connection and try refreshing the page\x1b[0m\r\n",
      );
    };

    this.ws.onclose = (event: CloseEvent) => {
      this.stopSpinner();
      console.log("[PTY] WebSocket closed:", event.code, event.reason);

      // Provide detailed close reason based on code
      // https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code
      let message = "";
      let reconnect = true;

      switch (event.code) {
        case 1000:
          message = "Session ended normally";
          reconnect = false;
          break;
        case 1001:
          message = "Server going away (maintenance or restart)";
          break;
        case 1006:
          message = "Connection lost (network issue or server unavailable)";
          break;
        case 1011:
          message = "Server error while processing request";
          break;
        case 1012:
          message = "Server restarting";
          break;
        case 1013:
          message = "Server overloaded, try again later";
          break;
        case 4000:
          message = "Authentication required - please log in";
          reconnect = false;
          break;
        case 4001:
          message = "Access denied - no permission for this project";
          reconnect = false;
          break;
        case 4002:
          message = "Project not found";
          reconnect = false;
          break;
        case 4003:
          message = "SLURM unavailable";
          reconnect = false;
          break;
        default:
          message =
            event.reason || `Connection closed (console: ${event.code})`;
      }

      this.term.write(`\r\n\x1b[1;33m⚠ Disconnected: ${message}\x1b[0m\r\n`);

      if (reconnect) {
        this.term.write("\x1b[0;36m   Reconnecting in 3s...\x1b[0m\r\n");
        setTimeout(() => this.connect(), 3000);
      } else {
        this.term.write("\x1b[0;33m   Refresh page to reconnect\x1b[0m\r\n");
      }
    };
  }

  private sendResize(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.term) {
      const rows = this.term.rows;
      const cols = this.term.cols;
      this.ws.send(`resize:${rows}:${cols}`);
    }
  }

  public write(text: string): void {
    if (this.term) {
      this.term.write(text);
    }
  }

  public writeln(text: string): void {
    if (this.term) {
      this.term.writeln(text);
    }
  }

  public clear(): void {
    if (this.term) {
      this.term.clear();
      console.log("[PTY] Terminal cleared");
    }

    // Also clear inline images and hide panel
    if (this.imageContainer) {
      this.imageContainer.innerHTML = "";
      this.imageContainer.style.display = "none";
      console.log("[PTY] Inline images cleared");
    }
  }

  /**
   * Get terminal theme from CSS custom properties
   */
  private getThemeFromCSS(): any {
    const root = document.documentElement;
    const style = getComputedStyle(root);

    return {
      background: style.getPropertyValue("--terminal-bg").trim(),
      foreground: style.getPropertyValue("--terminal-fg").trim(),
      cursor: style.getPropertyValue("--terminal-cursor").trim(),
      cursorAccent: style.getPropertyValue("--terminal-cursor-accent").trim(),
      black: style.getPropertyValue("--terminal-black").trim(),
      red: style.getPropertyValue("--terminal-red").trim(),
      green: style.getPropertyValue("--terminal-green").trim(),
      yellow: style.getPropertyValue("--terminal-yellow").trim(),
      blue: style.getPropertyValue("--terminal-blue").trim(),
      magenta: style.getPropertyValue("--terminal-magenta").trim(),
      cyan: style.getPropertyValue("--terminal-cyan").trim(),
      white: style.getPropertyValue("--terminal-white").trim(),
      brightBlack: style.getPropertyValue("--terminal-bright-black").trim(),
      brightRed: style.getPropertyValue("--terminal-bright-red").trim(),
      brightGreen: style.getPropertyValue("--terminal-bright-green").trim(),
      brightYellow: style.getPropertyValue("--terminal-bright-yellow").trim(),
      brightBlue: style.getPropertyValue("--terminal-bright-blue").trim(),
      brightMagenta: style.getPropertyValue("--terminal-bright-magenta").trim(),
      brightCyan: style.getPropertyValue("--terminal-bright-cyan").trim(),
      brightWhite: style.getPropertyValue("--terminal-bright-white").trim(),
    };
  }

  /**
   * Update terminal theme when global theme changes
   */
  public updateTheme(): void {
    if (!this.term) {
      console.warn("[PTY] Cannot update theme - terminal not initialized");
      return;
    }

    const newTheme = this.getThemeFromCSS();
    this.term.options.theme = newTheme;
    console.log("[PTY] Terminal theme updated from CSS");
  }

  public executeCommand(command: string): void {
    /**
     * Execute a command in the PTY terminal
     * This sends the command as if the user typed it and pressed Enter
     */
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      // Send command followed by Enter (\r)
      this.ws.send(command + "\r");
      console.log("[PTY] Executing command:", command);
    } else {
      console.error("[PTY] Cannot execute command - WebSocket not connected");
    }
  }

  public destroy(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.term) {
      this.term.dispose();
    }
  }

  public focus(): void {
    if (this.term) {
      this.term.focus();
    }
  }

  /**
   * Copy the full terminal buffer contents to the clipboard
   */
  public copyBuffer(): void {
    if (!this.term) {
      console.warn("[PTY] Cannot copy buffer - terminal not initialized");
      return;
    }

    const buffer = this.term.buffer.active;
    let text = "";
    for (let i = 0; i < buffer.length; i++) {
      const line = buffer.getLine(i);
      if (line) {
        text += line.translateToString(true) + "\n";
      }
    }

    // Trim trailing blank lines
    text = text.trimEnd() + "\n";

    navigator.clipboard
      .writeText(text)
      .then(() => {
        console.log("[PTY] Terminal buffer copied to clipboard");
      })
      .catch((err) => {
        console.error("[PTY] Failed to copy terminal buffer:", err);
      });
  }
}
