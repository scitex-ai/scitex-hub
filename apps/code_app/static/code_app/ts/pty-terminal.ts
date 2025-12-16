/**
 * Real PTY Terminal with xterm.js
 * Provides full interactive terminal with IPython, vim, etc.
 */

console.log("[DEBUG] apps/code_app/static/code_app/ts/pty-terminal.ts loaded");

export class PTYTerminal {
  private term: any;
  private ws: WebSocket | null = null;
  private projectId: number;
  private imageContainer: HTMLElement | null = null;
  private readyPromise: Promise<void>;
  private readyResolve!: () => void;

  constructor(containerEl: HTMLElement, projectId: number) {
    this.projectId = projectId;

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
      await new Promise(resolve => setTimeout(resolve, 100));
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
    });

    this.term.open(containerEl);

    // Fit addon for auto-resize
    if (FitAddon) {
      const fitAddon = new FitAddon();
      this.term.loadAddon(fitAddon);
      fitAddon.fit();

      // Resize on window resize
      window.addEventListener('resize', () => {
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
        console.log('[PTY] ✓ ImageAddon loaded successfully - inline images enabled');
      } catch (err) {
        console.error('[PTY] ✗ Failed to load ImageAddon:', err);
      }
    } else {
      console.warn('[PTY] ⚠ ImageAddon not available - window.ImageAddon is undefined');
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
          f: "/files/",
          s: "/scholar/",
          c: "/code/",
          v: "/vis/",
          w: "/writer/",
        };

        // Alt+Z: Toggle Zen Mode
        if (key === 'z') {
          console.log('[PTY] Alt+Z - Toggle Zen Mode');
          const zenEvent = new KeyboardEvent("keydown", {
            key: "F11",
            keyCode: 122,
            bubbles: true,
            cancelable: true,
          });
          document.dispatchEvent(zenEvent);
          return false;
        }

        // Module navigation (Alt+F/S/C/V/W)
        if (navigationRoutes[key]) {
          const route = navigationRoutes[key];
          if (!window.location.pathname.startsWith(route)) {
            console.log(`[PTY] Alt+${key.toUpperCase()} - Navigate to ${route}`);
            window.location.href = route;
          }
          return false; // Prevent terminal from receiving this
        }
      }

      // Ctrl+C or Ctrl+Shift+C: Copy selected text (if selection exists)
      if (event.ctrlKey && (event.key === 'C' || event.key === 'c')) {
        const selection = this.term.getSelection();
        if (selection) {
          navigator.clipboard.writeText(selection);
          console.log('[PTY] Copied to clipboard:', selection.substring(0, 50) + '...');
          return false; // Prevent default and don't send to terminal
        }
        // If no selection, allow Ctrl+C to send SIGINT to terminal
        return true;
      }

      // Ctrl+V or Ctrl+Shift+V: Paste from clipboard
      if (event.ctrlKey && (event.key === 'V' || event.key === 'v')) {
        navigator.clipboard.readText().then(text => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(text);
          }
        });
        return false; // Prevent default
      }

      return true; // Allow other keys
    });

    console.log('[PTY] xterm.js initialized');

    // Signal that initialization is complete
    this.readyResolve();
  }

  private connect(): void {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/code/terminal/?project_id=${this.projectId}`;

    console.log('[PTY] Connecting to:', wsUrl);

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[PTY] WebSocket connected');
      // No welcome message - PS1 already shows all necessary info
      this.sendResize();
    };

    this.ws.onmessage = (event) => {
      // Simply write all data to terminal - no inline image rendering
      this.term.write(event.data);
    };

    this.ws.onerror = (error) => {
      console.error('[PTY] WebSocket error:', error);
      this.term.write('\r\n\x1b[1;31mTerminal connection error\x1b[0m\r\n');
    };

    this.ws.onclose = () => {
      console.log('[PTY] WebSocket closed');
      this.term.write('\r\n\x1b[1;33m[Disconnected]\x1b[0m\r\n');

      // Attempt reconnect after 3 seconds
      setTimeout(() => this.connect(), 3000);
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
      console.log('[PTY] Terminal cleared');
    }

    // Also clear inline images and hide panel
    if (this.imageContainer) {
      this.imageContainer.innerHTML = '';
      this.imageContainer.style.display = 'none';
      console.log('[PTY] Inline images cleared');
    }
  }

  /**
   * Get terminal theme from CSS custom properties
   */
  private getThemeFromCSS(): any {
    const root = document.documentElement;
    const style = getComputedStyle(root);

    return {
      background: style.getPropertyValue('--terminal-bg').trim(),
      foreground: style.getPropertyValue('--terminal-fg').trim(),
      cursor: style.getPropertyValue('--terminal-cursor').trim(),
      cursorAccent: style.getPropertyValue('--terminal-cursor-accent').trim(),
      black: style.getPropertyValue('--terminal-black').trim(),
      red: style.getPropertyValue('--terminal-red').trim(),
      green: style.getPropertyValue('--terminal-green').trim(),
      yellow: style.getPropertyValue('--terminal-yellow').trim(),
      blue: style.getPropertyValue('--terminal-blue').trim(),
      magenta: style.getPropertyValue('--terminal-magenta').trim(),
      cyan: style.getPropertyValue('--terminal-cyan').trim(),
      white: style.getPropertyValue('--terminal-white').trim(),
      brightBlack: style.getPropertyValue('--terminal-bright-black').trim(),
      brightRed: style.getPropertyValue('--terminal-bright-red').trim(),
      brightGreen: style.getPropertyValue('--terminal-bright-green').trim(),
      brightYellow: style.getPropertyValue('--terminal-bright-yellow').trim(),
      brightBlue: style.getPropertyValue('--terminal-bright-blue').trim(),
      brightMagenta: style.getPropertyValue('--terminal-bright-magenta').trim(),
      brightCyan: style.getPropertyValue('--terminal-bright-cyan').trim(),
      brightWhite: style.getPropertyValue('--terminal-bright-white').trim(),
    };
  }

  /**
   * Update terminal theme when global theme changes
   */
  public updateTheme(): void {
    if (!this.term) {
      console.warn('[PTY] Cannot update theme - terminal not initialized');
      return;
    }

    const newTheme = this.getThemeFromCSS();
    this.term.options.theme = newTheme;
    console.log('[PTY] Terminal theme updated from CSS');
  }

  public executeCommand(command: string): void {
    /**
     * Execute a command in the PTY terminal
     * This sends the command as if the user typed it and pressed Enter
     */
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      // Send command followed by Enter (\r)
      this.ws.send(command + '\r');
      console.log('[PTY] Executing command:', command);
    } else {
      console.error('[PTY] Cannot execute command - WebSocket not connected');
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
}
