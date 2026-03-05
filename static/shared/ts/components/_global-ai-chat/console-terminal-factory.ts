/**
 * Terminal Instance Factory for Console Mode
 *
 * Creates and configures individual xterm.js terminal instances.
 * Each instance gets its own terminal, fit addon, WebSocket, and event handlers.
 */

import { registerZoomZone } from "../context-zoom";
import { uploadFiles } from "../../utils/file-upload";
import { speakText } from "./speech";

export interface TerminalInstance {
  terminal: any;
  fitAddon: any;
  ws: WebSocket | null;
  connected: boolean;
  resizeObserver: ResizeObserver | null;
  resizeTimeout: ReturnType<typeof setTimeout> | null;
}

const XTERM_JS_URL = "https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js";
const XTERM_CSS_URL = "https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css";
const FIT_ADDON_URL =
  "https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js";

let cachedTerminal: any = null;
let cachedFitAddon: any = null;

export async function loadXtermModules(): Promise<{
  Terminal: any;
  FitAddon: any;
}> {
  if (cachedTerminal)
    return { Terminal: cachedTerminal, FitAddon: cachedFitAddon };

  const win = window as any;
  const [xtermCode, fitCode] = await Promise.all([
    fetch(XTERM_JS_URL).then((r) => r.text()),
    fetch(FIT_ADDON_URL).then((r) => r.text()),
  ]);
  const savedDefine = win.define;
  const savedRequire = win.require;
  win.define = undefined;
  win.require = undefined;
  try {
    new Function(xtermCode)();
    new Function(fitCode)();
  } finally {
    win.define = savedDefine;
    win.require = savedRequire;
  }
  cachedTerminal = win.Terminal?.Terminal || win.Terminal;
  cachedFitAddon = win.FitAddon?.FitAddon || win.FitAddon;
  return { Terminal: cachedTerminal, FitAddon: cachedFitAddon };
}

export function loadXtermCSS(): void {
  if (document.querySelector(`link[href="${XTERM_CSS_URL}"]`)) return;
  const el = document.createElement("link");
  el.rel = "stylesheet";
  el.href = XTERM_CSS_URL;
  document.head.appendChild(el);
}

export function getTerminalTheme(): Record<string, string> {
  const s = getComputedStyle(document.documentElement);
  const get = (v: string, fb: string) => s.getPropertyValue(v).trim() || fb;
  const isDark =
    document.documentElement.getAttribute("data-theme") !== "light";
  return isDark
    ? {
        background: get("--terminal-bg", "#0d1117"),
        foreground: get("--terminal-fg", "#c9d1d9"),
        cursor: get("--terminal-cursor", "#58a6ff"),
      }
    : {
        background: get("--terminal-bg", "#ffffff"),
        foreground: get("--terminal-fg", "#24292f"),
        cursor: get("--terminal-cursor", "#0969da"),
      };
}

/** Create a terminal instance with xterm.js, fit addon, and event handlers */
export function createTerminalInstance(
  container: HTMLElement,
  TerminalClass: any,
  FitAddonClass: any,
): TerminalInstance | null {
  if (!TerminalClass) return null;

  const terminal = new TerminalClass({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
    theme: getTerminalTheme(),
    scrollback: 10000,
  });

  terminal.open(container);

  const inst: TerminalInstance = {
    terminal,
    fitAddon: null,
    ws: null,
    connected: false,
    resizeObserver: null,
    resizeTimeout: null,
  };

  if (FitAddonClass) {
    inst.fitAddon = new FitAddonClass();
    terminal.loadAddon(inst.fitAddon);
    fitInstance(inst);

    inst.resizeObserver = new ResizeObserver(() => {
      if (inst.resizeTimeout) clearTimeout(inst.resizeTimeout);
      inst.resizeTimeout = setTimeout(() => fitInstance(inst), 100);
    });
    inst.resizeObserver.observe(container);
  }

  terminal.onData((data: string) => {
    if (inst.ws?.readyState === WebSocket.OPEN) inst.ws.send(data);
  });

  setupDropHandlers(container, inst);
  setupRightClickHandler(container, inst);
  setupClipboardHandler(terminal, inst);
  setupZoom(container, inst);

  return inst;
}

/** Connect a terminal instance via WebSocket */
export function connectInstance(
  inst: TerminalInstance,
  onStatusChange?: (
    state: "connecting" | "connected" | "disconnected" | "error",
  ) => void,
): void {
  if (inst.connected || !inst.terminal) return;
  onStatusChange?.("connecting");

  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const projectId =
    document.querySelector<HTMLElement>(".project-selector-btn")?.dataset
      .activeProjectId || "0";
  const url = `${proto}//${window.location.host}/ws/console/terminal/?project_id=${projectId}`;

  inst.ws = new WebSocket(url);

  inst.ws.onopen = () => {
    inst.connected = true;
    onStatusChange?.("connected");
    sendResizeForInstance(inst);
  };

  inst.ws.onmessage = (ev) => {
    const data: string = ev.data;
    const processed = handleOscEscapes(data, inst);
    if (processed) inst.terminal.write(processed);
  };

  inst.ws.onerror = () => onStatusChange?.("error");

  inst.ws.onclose = (ev) => {
    inst.connected = false;
    if (ev.code === 1000) {
      onStatusChange?.("disconnected");
    } else {
      onStatusChange?.("error");
      setTimeout(() => connectInstance(inst, onStatusChange), 3000);
    }
  };
}

export function fitInstance(inst: TerminalInstance): void {
  if (inst.fitAddon) {
    try {
      inst.fitAddon.fit();
      sendResizeForInstance(inst);
    } catch {
      /* container may be hidden */
    }
  }
}

export function sendResizeForInstance(inst: TerminalInstance): void {
  if (inst.ws?.readyState === WebSocket.OPEN && inst.terminal) {
    inst.ws.send(`resize:${inst.terminal.rows}:${inst.terminal.cols}`);
  }
}

export function destroyInstance(inst: TerminalInstance): void {
  inst.resizeObserver?.disconnect();
  if (inst.resizeTimeout) clearTimeout(inst.resizeTimeout);
  inst.ws?.close();
  inst.terminal?.dispose();
}

/* ── Per-Instance Setup Helpers ─────────────────────── */

function setupDropHandlers(
  container: HTMLElement,
  inst: TerminalInstance,
): void {
  container.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    container.classList.add("drop-target");
  });
  container.addEventListener("dragleave", () => {
    container.classList.remove("drop-target");
  });
  container.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    container.classList.remove("drop-target");
    const dt = e.dataTransfer;
    if (!dt) return;
    if (dt.files && dt.files.length > 0) {
      void (async () => {
        try {
          const paths = await uploadFiles(dt.files);
          if (inst.ws?.readyState === WebSocket.OPEN) {
            inst.ws.send(paths.join(" "));
          }
        } catch (err) {
          console.error("[Console] File upload error:", err);
        }
      })();
      return;
    }
    const raw = dt.getData("text/plain") ?? "";
    const paths = raw.split(";").filter(Boolean);
    if (paths.length > 0 && inst.ws?.readyState === WebSocket.OPEN) {
      inst.ws.send(paths.join(" "));
    }
  });
}

function setupRightClickHandler(
  container: HTMLElement,
  inst: TerminalInstance,
): void {
  let rightClickCount = 0;
  let rightClickTimer: ReturnType<typeof setTimeout> | null = null;
  const RIGHT_CLICK_WINDOW = 400;

  container.addEventListener("contextmenu", (e: MouseEvent) => {
    e.preventDefault();
    rightClickCount++;
    if (rightClickTimer) clearTimeout(rightClickTimer);
    rightClickTimer = setTimeout(() => {
      const count = Math.min(rightClickCount, 4);
      rightClickCount = 0;
      rightClickTimer = null;
      if (inst.ws?.readyState === WebSocket.OPEN) {
        inst.ws.send(String(count));
        setTimeout(() => {
          if (inst.ws?.readyState === WebSocket.OPEN) inst.ws.send("\r");
        }, 500);
      }
    }, RIGHT_CLICK_WINDOW);
  });
}

function setupClipboardHandler(terminal: any, inst: TerminalInstance): void {
  terminal.attachCustomKeyEventHandler((ev: KeyboardEvent) => {
    if (ev.ctrlKey && (ev.key === "c" || ev.key === "C")) {
      const sel = terminal.getSelection();
      if (sel) {
        navigator.clipboard.writeText(sel);
        return false;
      }
      return true;
    }
    if (ev.ctrlKey && (ev.key === "v" || ev.key === "V")) {
      navigator.clipboard.readText().then((t: string) => {
        if (inst.ws?.readyState === WebSocket.OPEN) inst.ws.send(t);
      });
      return false;
    }
    if (ev.altKey && ev.key === "a") return false;
    return true;
  });
}

function setupZoom(container: HTMLElement, inst: TerminalInstance): void {
  registerZoomZone({
    el: container,
    getSize: () => inst.terminal?.options?.fontSize ?? 13,
    setSize: (px) => {
      if (inst.terminal) {
        inst.terminal.options.fontSize = px;
        fitInstance(inst);
      }
    },
    min: 8,
    max: 24,
    default: 13,
    storageKey: "scitex-terminal-font-size",
  });
}

/* ── OSC Escape Handling ──────────────────────────────── */

function handleOscEscapes(data: string, inst: TerminalInstance): string | null {
  let remaining = data;
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
  remaining = extractOsc(remaining, "\x1b]9998;media:", (b64) => {
    try {
      const ref = JSON.parse(atob(b64));
      showMediaOverlay(ref, inst);
    } catch {
      /* ignore */
    }
  });
  return remaining || null;
}

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

function showMediaOverlay(
  ref: { type: string; path: string; url?: string },
  inst: TerminalInstance,
): void {
  const container = inst.terminal?.element?.parentElement;
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
  setTimeout(() => overlay.remove(), 15000);
}
