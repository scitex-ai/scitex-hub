/**
 * Console Project Switch Handler
 * Sends `cd` to terminal on project switch, with idle detection.
 * When terminal is busy, shows toast with manual cd instruction.
 */

import { showToast } from "../../utils/ui";

/**
 * Check if terminal appears idle (at a shell prompt).
 * Inspects the current cursor line for common prompt patterns.
 */
function isTerminalIdle(terminal: any): boolean {
  try {
    const buf = terminal.buffer?.active;
    if (!buf) return false;
    const cursorY = buf.cursorY;
    const line = buf.getLine(cursorY + buf.baseY);
    if (!line) return false;
    const text = line.translateToString(true).trimEnd();
    // Common shell prompt endings: $, #, >, %, or claude prompt ❯
    return /[$#>%❯]\s*$/.test(text) || text === "";
  } catch {
    return false;
  }
}

/**
 * Set up project switch listener for a console mode instance.
 * @param getWs - Returns the active WebSocket
 * @param getTerminal - Returns the active xterm Terminal
 */
export function setupProjectSwitchHandler(
  getWs: () => WebSocket | null,
  getTerminal: () => any | null,
): void {
  window.addEventListener("scitex:project-switched", ((
    e: CustomEvent<{ projectSlug: string }>,
  ) => {
    const ws = getWs();
    const term = getTerminal();
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    const slug = e.detail.projectSlug;
    const cdCmd = `cd ~/proj/${slug}\n`;

    if (term && isTerminalIdle(term)) {
      ws.send(cdCmd);
    } else {
      showToast(`Run: cd ~/proj/${slug}`, "info");
    }
  }) as EventListener);
}
