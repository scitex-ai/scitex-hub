/**
 * PTY session-state message handling — extracted from _pty-terminal.ts
 * (512-line cap). Renders allocation/lifecycle state changes into the
 * terminal + status badge and raises background notifications. No
 * WebSocket or xterm state lives here; the caller passes a writer and
 * overlay callbacks.
 */

/** Minimal terminal writer the state handler needs. */
export interface SessionStateTerm {
  write(text: string): void;
}

/** Callbacks back into PTYTerminal for overlay effects. */
export interface SessionStateHooks {
  /** Hide any restart overlay (state became "running"). */
  hideRestartOverlay(): void;
  /** Show the prominent restart overlay (state became "dead"). */
  showRestartOverlay(reason: string): void;
}

/** Send a browser notification for background-tab awareness. */
function notifyUser(message: string): void {
  if (
    document.hidden &&
    "Notification" in window &&
    Notification.permission === "granted"
  ) {
    new Notification("SciTeX Terminal", { body: message });
  }
}

/** Update the status badge text and style. */
function updateBadge(
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

/**
 * Handle a `session_state` control message: write the state transition
 * into the terminal, update the status badge, and fire overlay /
 * notification hooks. Returns the new state string.
 */
export function handleSessionStateMessage(
  msg: any,
  term: SessionStateTerm,
  hooks: SessionStateHooks,
): string {
  const state = msg.state;
  console.log("[PTY] Session state:", state, msg);

  const badge = document.getElementById("terminal-session-status");

  switch (state) {
    case "allocation_starting":
      term.write(
        "\r\n\x1b[1;36m Preparing your computing environment...\x1b[0m\r\n",
      );
      updateBadge(badge, "starting", "warning");
      break;

    case "allocation_expiring": {
      const remaining = msg.remaining || 0;
      const minutes = Math.ceil(remaining / 60);
      const timeStr = minutes > 0 ? `${minutes} min` : `${remaining}s`;
      term.write(`\r\n\x1b[1;33m ⚠ Session expires in ${timeStr}\x1b[0m\r\n`);
      term.write(
        "\x1b[0;33m   Save your work. A new session will start automatically.\x1b[0m\r\n",
      );
      updateBadge(badge, `expires ${timeStr}`, "warning");
      notifyUser(`Terminal session expires in ${timeStr}`);
      break;
    }

    case "allocation_dead": {
      const reason = msg.reason || "Unknown reason";
      term.write(`\r\n\x1b[1;31m ❌ Session ended: ${reason}\x1b[0m\r\n`);
      term.write("\x1b[0;36m   Reconnecting automatically...\x1b[0m\r\n");
      updateBadge(badge, "reconnecting", "warning");
      notifyUser(`Session ended: ${reason}. Reconnecting...`);
      break;
    }

    case "allocation_recovering":
      term.write(
        "\r\n\x1b[1;36m Preparing your computing environment...\x1b[0m\r\n",
      );
      updateBadge(badge, "reconnecting", "warning");
      break;

    case "exited":
    case "respawning":
      term.write("\r\n\x1b[1;33m Restarting terminal...\x1b[0m\r\n");
      updateBadge(badge, "restarting", "warning");
      break;

    case "running":
      hooks.hideRestartOverlay();
      updateBadge(badge, "", "");
      break;

    case "dead": {
      const deadReason = msg.reason || "Terminal stopped";
      term.write(`\r\n\x1b[1;31m ❌ ${deadReason}\x1b[0m\r\n`);
      updateBadge(badge, "stopped", "error");
      notifyUser(deadReason);
      hooks.showRestartOverlay(deadReason);
      break;
    }
  }

  return state;
}
