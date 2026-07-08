/**
 * PTY terminal UI helpers — pure DOM builders extracted from
 * _pty-terminal.ts (512-line cap): CSS-variable theme reader and the
 * restart / reconnect overlays. No WebSocket or xterm state in here.
 */

/** Read the xterm.js theme from workspace CSS variables. */
export function getTerminalThemeFromCSS(): any {
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

/** Remove any restart/reconnect overlay from the terminal container. */
export function hideTerminalOverlay(containerEl: HTMLElement): void {
  containerEl.querySelector(".terminal-restart-overlay")?.remove();
}

/** Show a prominent restart overlay over the terminal. */
export function showTerminalRestartOverlay(
  containerEl: HTMLElement,
  reason: string,
  onRestart: () => void,
  onNewTerminal: () => void,
): void {
  hideTerminalOverlay(containerEl);
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
      hideTerminalOverlay(containerEl);
      onRestart();
    });
  overlay.querySelector(".terminal-new-btn")?.addEventListener("click", () => {
    hideTerminalOverlay(containerEl);
    onNewTerminal();
  });
  containerEl.style.position = "relative";
  containerEl.appendChild(overlay);
}

/** Show a click-to-reconnect overlay over the terminal. */
export function showTerminalReconnectPrompt(
  containerEl: HTMLElement,
  reason: string,
  onReconnect: () => void,
): void {
  hideTerminalOverlay(containerEl);
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
      hideTerminalOverlay(containerEl);
      onReconnect();
    });
  containerEl.style.position = "relative";
  containerEl.appendChild(overlay);
}
