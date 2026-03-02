/**
 * Chat Config Limits — populates Daily Limits into the chat settings popover.
 * Fetches from /accounts/api/ai-limits/ and renders inline.
 */

import { renderLimits, bindLimitsInputs } from "./config-limits";

/** Populate limits into #ai-chat-limits-content (once). */
export async function populateChatLimits(): Promise<void> {
  const container = document.getElementById("ai-chat-limits-content");
  if (!container || container.dataset.loaded) return;
  try {
    const resp = await fetch("/accounts/api/ai-limits/").then((r) => r.json());
    container.innerHTML = renderLimits(resp);
    bindLimitsInputs(container, () => {});
    container.dataset.loaded = "1";
  } catch {
    /* silent */
  }
}
