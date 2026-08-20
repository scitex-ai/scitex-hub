/**
 * Comms app -- barrel export + auto-mount.
 *
 * This is the Vite entry point loaded by comms_partial.html
 * (`{% vite_script 'comms_app/index' %}`). Mounts ChatPanel onto
 * #comms-root when present, same self-init convention as
 * discovery_app/ts/index.ts.
 */

import { ChatPanel } from "./chat-panel";
import { CommsClient } from "./comms-client";

export { CommsClient, ChatPanel };
export type {
  Channel,
  ErrorEvent,
  EventHandler,
  Message,
  MessageEvent,
  MessageSender,
  Participant,
  PresenceEvent,
  ServerEvent,
  ServerEventType,
  TypingEvent,
} from "./types";

function initComms(): void {
  if (!document.getElementById("comms-root")) return;
  new ChatPanel("#comms-root");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initComms);
} else {
  initComms();
}
