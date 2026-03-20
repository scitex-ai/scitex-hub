/**
 * SSE Stream Handler for AI Chat
 * Processes Server-Sent Events from /apps/llm/api/chat/stream/
 */

import { setModelBadge } from "./model-badge";
import { appendToolTags } from "./tool-tags";
import { StoredMessage, saveMessage } from "./storage";
import { runUIActions, UIActionArgs } from "../ui-action/index";
import { renderMedia, MediaRef } from "./media-renderer";
import {
  renderMarkdown,
  highlightCodeBlocks,
  fixExternalLinks,
} from "./markdown-render";

export interface StreamContext {
  messagesEl: HTMLElement;
  modelBadge: HTMLElement | null;
  speak: (text: string) => void;
  autoSpeak: boolean;
  scrollIfNeeded?: () => void;
}

const RENDER_DEBOUNCE_MS = 150;

/** Flush accumulated text buffer as rendered markdown into a container */
function flushTextBuffer(
  textBuf: string,
  msgEl: HTMLElement,
): HTMLElement | null {
  if (!textBuf.trim()) return null;
  const wrapper = document.createElement("div");
  wrapper.className = "ai-md-segment";
  wrapper.innerHTML = renderMarkdown(textBuf);
  highlightCodeBlocks(wrapper);
  fixExternalLinks(wrapper);
  msgEl.appendChild(wrapper);
  return wrapper;
}

/** Process SSE stream and render assistant response */
export async function processStream(
  resp: Response,
  msgEl: HTMLElement,
  ctx: StreamContext,
): Promise<void> {
  const toolsUsed: string[] = [];
  const mediaRefs: MediaRef[] = [];
  let contextUser = "";
  let contextSlug = "";
  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // Text accumulator for markdown rendering
  let textBuf = "";
  let previewEl: HTMLElement | null = null;
  let renderTimer: ReturnType<typeof setTimeout> | null = null;

  /** Debounced live preview of accumulated text */
  function schedulePreview(): void {
    if (renderTimer) clearTimeout(renderTimer);
    renderTimer = setTimeout(() => {
      if (!textBuf.trim()) return;
      if (!previewEl) {
        previewEl = document.createElement("div");
        previewEl.className = "ai-md-segment ai-md-streaming";
        msgEl.appendChild(previewEl);
      }
      previewEl.innerHTML = renderMarkdown(textBuf);
      if (ctx.scrollIfNeeded) ctx.scrollIfNeeded();
      else
        requestAnimationFrame(() => {
          ctx.messagesEl.scrollTop = ctx.messagesEl.scrollHeight;
        });
    }, RENDER_DEBOUNCE_MS);
  }

  /** Finalize the current text segment: replace preview with final render */
  function finalizeTextSegment(): void {
    if (renderTimer) clearTimeout(renderTimer);
    renderTimer = null;
    if (previewEl) {
      previewEl.remove();
      previewEl = null;
    }
    flushTextBuffer(textBuf, msgEl);
    textBuf = "";
  }

  // Track raw text for storage
  let fullText = "";

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
        const chunk = event.text as string;
        textBuf += chunk;
        fullText += chunk;
        schedulePreview();
      } else if (event.type === "tool_start") {
        // Flush text before tool tag
        finalizeTextSegment();
        toolsUsed.push(event.name as string);
        appendToolTags(msgEl, [event.name as string]);
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
      } else if (event.type === "file_ops") {
        const ops = event.ops as { path: string; op: string }[];
        if (ops?.length) {
          for (const op of ops) {
            const badge = document.createElement("span");
            badge.className = `stx-shell-ai-file-op stx-shell-ai-file-op--${op.op}`;
            const icon =
              op.op === "created"
                ? "fa-plus-circle"
                : op.op === "modified"
                  ? "fa-pen"
                  : op.op === "moved"
                    ? "fa-arrow-right"
                    : "fa-trash";
            const parts = op.path.split("/");
            const fname = parts.pop() || op.path;
            const dir = parts.length > 0 ? parts.join("/") + "/" : "";
            badge.innerHTML = dir
              ? `<i class="fas ${icon}"></i> <span class="stx-shell-ai-file-op-dir">${dir}</span>${fname}`
              : `<i class="fas ${icon}"></i> ${fname}`;
            msgEl.appendChild(badge);
          }
          if (ctx.scrollIfNeeded) ctx.scrollIfNeeded();
        }
      } else if (event.type === "tool_result") {
        const media = event.media as MediaRef[] | undefined;
        if (media?.length && contextUser && contextSlug) {
          for (const ref of media) {
            mediaRefs.push(ref);
            msgEl.appendChild(renderMedia(ref, contextUser, contextSlug));
          }
          if (ctx.scrollIfNeeded) ctx.scrollIfNeeded();
          else
            requestAnimationFrame(() => {
              ctx.messagesEl.scrollTop = ctx.messagesEl.scrollHeight;
            });
        }
      } else if (event.type === "error") {
        finalizeTextSegment();
        msgEl.remove();
        const errEl = document.createElement("div");
        errEl.className = "stx-shell-ai-msg error";
        ctx.messagesEl.appendChild(errEl);
        errEl.textContent = `AI request failed: ${event.error as string}`;
        saveMessage({ role: "error", text: errEl.textContent });
      }
    }
  }

  // Flush any remaining text
  finalizeTextSegment();

  // Refresh file tree if AI wrote files
  const fileTools = [
    "project_write_file",
    "project_exec_python",
    "project_exec_shell",
  ];
  if (
    toolsUsed.some((t) => fileTools.includes(t)) &&
    window.workspaceFilesTree
  ) {
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
  if (fullText || toolsUsed.length > 0 || mediaRefs.length > 0) {
    saveMessage({
      role: "assistant",
      text: fullText,
      toolsUsed,
      media: mediaRefs.length > 0 ? mediaRefs : undefined,
    } as StoredMessage);
    if (fullText && ctx.autoSpeak && !toolsUsed.includes("audio_speak"))
      ctx.speak(fullText);
  }
}
