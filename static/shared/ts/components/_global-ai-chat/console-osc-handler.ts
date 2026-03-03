/**
 * Console OSC Escape Handler
 *
 * Processes OSC escape sequences from the terminal output stream:
 * - OSC 9999: Text-to-speech relay
 * - OSC 9998: Media overlay display
 */

import { speakText } from "./speech";

/** Extract and handle a single OSC escape, return data with escape removed. */
function extractOsc(
  data: string,
  prefix: string,
  handler: (b64: string) => void,
): string {
  const idx = data.indexOf(prefix);
  if (idx === -1) return data;
  const start = idx + prefix.length;
  const end = data.indexOf("\x07", start);
  if (end === -1) return data;
  handler(data.slice(start, end));
  return data.slice(0, idx) + data.slice(end + 1);
}

/**
 * Process OSC escape sequences (speech + media), return remaining data to write.
 * Returns null if all data was consumed by escapes.
 */
export function handleOscEscapes(
  data: string,
  container: HTMLElement | null,
): string | null {
  let remaining = data;

  // TTS: \x1b]9999;speak:<base64>\x07
  remaining = extractOsc(remaining, "\x1b]9999;speak:", (b64) => {
    try {
      const text = atob(b64);
      const csrf =
        document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
          ?.value ??
        (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "");
      speakText(text, csrf);
    } catch {
      /* ignore */
    }
  });

  // Session state: \x1b]9997;{json}\x07
  remaining = extractOsc(remaining, "\x1b]9997;", (payload) => {
    try {
      const msg = JSON.parse(payload);
      container?.dispatchEvent(
        new CustomEvent("scitex-session-state", { detail: msg, bubbles: true }),
      );
    } catch {
      /* ignore malformed */
    }
  });

  // Media: \x1b]9998;media:<base64-json>\x07
  remaining = extractOsc(remaining, "\x1b]9998;media:", (b64) => {
    try {
      const ref = JSON.parse(atob(b64));
      showMediaOverlay(ref, container);
    } catch {
      /* ignore */
    }
  });

  return remaining || null;
}

/** Show a floating media overlay above the terminal. */
function showMediaOverlay(
  ref: { type: string; path: string; url?: string },
  container: HTMLElement | null,
): void {
  if (!container) return;
  const overlay = document.createElement("div");
  overlay.className = "scitex-terminal-media-overlay";
  const closeBtn = document.createElement("button");
  closeBtn.className = "scitex-terminal-media-close";
  closeBtn.innerHTML = "&times;";
  closeBtn.onclick = () => overlay.remove();
  overlay.appendChild(closeBtn);

  const url = ref.url || ref.path;
  if (ref.type === "image") {
    const img = document.createElement("img");
    img.src = url;
    img.style.maxWidth = "100%";
    img.style.maxHeight = "80%";
    overlay.appendChild(img);
  } else {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.textContent = ref.path.split("/").pop() || ref.path;
    link.style.color = "var(--color-accent-fg, #58a6ff)";
    overlay.appendChild(link);
  }

  container.style.position = "relative";
  container.appendChild(overlay);
  // Auto-dismiss after 15s
  setTimeout(() => overlay.remove(), 15000);
}
