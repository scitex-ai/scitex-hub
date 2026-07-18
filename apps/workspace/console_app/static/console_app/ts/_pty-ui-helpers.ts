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

/** Build an <i> icon element with the given Font Awesome classes. */
function icon(faClasses: string): HTMLElement {
  const el = document.createElement("i");
  el.className = faClasses;
  return el;
}

/** Build a button with an icon and a text label (no HTML injection). */
function overlayButton(
  className: string,
  faClasses: string,
  label: string,
  onClick: () => void,
): HTMLButtonElement {
  const btn = document.createElement("button");
  btn.className = className;
  btn.appendChild(icon(faClasses));
  btn.appendChild(document.createTextNode(` ${label}`));
  btn.addEventListener("click", onClick);
  return btn;
}

/** Build the shared overlay scaffold. `reason` may include text derived
 * from server/WebSocket messages, so it is set via textContent — never
 * interpolated into markup (CodeQL js/xss). */
function buildOverlay(
  containerEl: HTMLElement,
  faClasses: string,
  reason: string,
  buttons: HTMLButtonElement[],
): void {
  hideTerminalOverlay(containerEl);
  const overlay = document.createElement("div");
  overlay.className = "terminal-restart-overlay";
  const content = document.createElement("div");
  content.className = "terminal-restart-content";
  content.appendChild(icon(faClasses));
  const message = document.createElement("p");
  message.textContent = reason;
  content.appendChild(message);
  for (const btn of buttons) content.appendChild(btn);
  overlay.appendChild(content);
  containerEl.style.position = "relative";
  containerEl.appendChild(overlay);
}

/** Show a prominent restart overlay over the terminal. */
export function showTerminalRestartOverlay(
  containerEl: HTMLElement,
  reason: string,
  onRestart: () => void,
  onNewTerminal: () => void,
): void {
  buildOverlay(containerEl, "fas fa-exclamation-triangle", reason, [
    overlayButton(
      "terminal-restart-btn",
      "fas fa-redo",
      "Restart Terminal",
      () => {
        hideTerminalOverlay(containerEl);
        onRestart();
      },
    ),
    overlayButton("terminal-new-btn", "fas fa-plus", "New Terminal", () => {
      hideTerminalOverlay(containerEl);
      onNewTerminal();
    }),
  ]);
}

/** Show a click-to-reconnect overlay over the terminal. */
export function showTerminalReconnectPrompt(
  containerEl: HTMLElement,
  reason: string,
  onReconnect: () => void,
): void {
  buildOverlay(containerEl, "fas fa-plug", reason, [
    overlayButton(
      "terminal-reconnect-btn",
      "fas fa-wifi",
      "Click to Reconnect",
      () => {
        hideTerminalOverlay(containerEl);
        onReconnect();
      },
    ),
  ]);
}
