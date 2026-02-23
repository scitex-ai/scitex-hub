/**
 * SSE Stream Handler for AI Chat
 * Processes Server-Sent Events from /llm/api/chat/stream/
 */

import { setModelBadge } from "./model-badge";
import { appendToolTags } from "./tool-tags";
import { StoredMessage, saveMessage } from "./storage";
import { runUIActions, UIActionArgs } from "../ui-action/index";
import { renderMedia, MediaRef } from "./media-renderer";

export interface StreamContext {
  messagesEl: HTMLElement;
  modelBadge: HTMLElement | null;
  speak: (text: string) => void;
  autoSpeak: boolean;
}

/** Process SSE stream and render assistant response */
export async function processStream(
  resp: Response,
  msgEl: HTMLElement,
  ctx: StreamContext,
): Promise<void> {
  let hasText = false;
  const toolsUsed: string[] = [];
  const mediaRefs: MediaRef[] = [];
  let contextUser = "";
  let contextSlug = "";
  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (raw === "[DONE]") break;
      let event: Record<string, unknown>;
      try {
        event = JSON.parse(raw);
      } catch {
        continue;
      }

      if (event.type === "model") {
        setModelBadge(ctx.modelBadge, event.name as string);
      } else if (event.type === "chunk") {
        if (!hasText) {
          msgEl.appendChild(document.createTextNode(event.text as string));
          hasText = true;
        } else {
          let last: Text | null = null;
          for (const node of msgEl.childNodes)
            if (node.nodeType === Node.TEXT_NODE) last = node as Text;
          if (last) last.textContent += event.text as string;
        }
        ctx.messagesEl.scrollTop = ctx.messagesEl.scrollHeight;
      } else if (event.type === "tool_start") {
        toolsUsed.push(event.name as string);
        appendToolTags(msgEl, [event.name as string]);
        hasText = false;
        if (event.name === "audio_speak" && event.args) {
          try {
            const a = JSON.parse(event.args as string) as Record<
              string,
              unknown
            >;
            if (a.text) ctx.speak(a.text as string);
          } catch {
            /**/
          }
        }
        if (event.name === "ui_action" && event.args) {
          try {
            void runUIActions(JSON.parse(event.args as string) as UIActionArgs);
          } catch {
            /**/
          }
        }
      } else if (event.type === "context") {
        contextUser = event.username as string;
        contextSlug = event.slug as string;
      } else if (event.type === "tool_result") {
        const media = event.media as MediaRef[] | undefined;
        if (media?.length && contextUser && contextSlug) {
          for (const ref of media) {
            mediaRefs.push(ref);
            msgEl.appendChild(renderMedia(ref, contextUser, contextSlug));
          }
          ctx.messagesEl.scrollTop = ctx.messagesEl.scrollHeight;
        }
      } else if (event.type === "error") {
        msgEl.remove();
        const errEl = document.createElement("div");
        errEl.className = "scitex-ai-msg error";
        ctx.messagesEl.appendChild(errEl);
        errEl.textContent = `AI request failed: ${event.error as string}`;
        saveMessage({ role: "error", text: errEl.textContent });
      }
    }
  }

  // Refresh file tree if AI wrote files
  if (toolsUsed.includes("project_write_file") && window.workspaceFilesTree) {
    setTimeout(() => {
      window.workspaceFilesTree?.refresh();
      const treeEl = document.getElementById("file-tree");
      if (treeEl) {
        treeEl.classList.remove("wft-ai-refresh-flash");
        void treeEl.offsetWidth;
        treeEl.classList.add("wft-ai-refresh-flash");
      }
    }, 300);
  }

  // Save and optionally speak
  const msgText = Array.from(msgEl.childNodes)
    .filter((n) => n.nodeType === Node.TEXT_NODE)
    .map((n) => n.textContent ?? "")
    .join("");
  if (msgText || toolsUsed.length > 0 || mediaRefs.length > 0) {
    saveMessage({
      role: "assistant",
      text: msgText,
      toolsUsed,
      media: mediaRefs.length > 0 ? mediaRefs : undefined,
    } as StoredMessage);
    if (msgText && ctx.autoSpeak && !toolsUsed.includes("audio_speak"))
      ctx.speak(msgText);
  }
}
