/** AI Panel Console Mode — multi-terminal tabs with camera/sketch/mic toolbar. */

import { registerZoomZone } from "../context-zoom";
import { uploadFiles } from "../../utils/file-upload";
import { SketchCanvas } from "./sketch-canvas";
import { WebcamCapture } from "./webcam-capture";
import { VoiceRecorder } from "./recorder";
import { getCsrfToken } from "../../utils/csrf";
import { setupAutoAccept } from "./console-auto-accept";
import { handleOscEscapes } from "./console-osc-handler";
import { ConsoleTabManager, type ConsoleTab } from "./console-tabs";
import {
  preventNavKeyDefault,
  setupFileDrop,
  setupRightClick,
} from "./console-event-handlers";
import { setupProjectSwitchHandler } from "./console-project-switch";
import {
  showAllocationSpinner,
  hideAllocationSpinner,
} from "./console-allocation-spinner";

/** Adapter: WebcamCapture/SketchCanvas → upload image → type path into terminal */
function makeImageSink(send: (t: string) => void) {
  return {
    addImageFromDataUrl(dataUrl: string, mime: string) {
      const b = atob(dataUrl.split(",")[1]);
      const u8 = Uint8Array.from(b, (c) => c.charCodeAt(0));
      const ext = mime === "image/jpeg" ? "jpg" : "png";
      const f = new File([u8], `capture.${ext}`, { type: mime });
      const dt = new DataTransfer();
      dt.items.add(f);
      void uploadFiles(dt.files).then((p) => send(p.join(" ")));
    },
  };
}

export interface ConsoleToolbarRefs {
  cameraBtn: HTMLButtonElement | null;
  sketchBtn: HTMLButtonElement | null;
  micBtn: HTMLButtonElement | null;
  fileInput: HTMLInputElement | null;
}

interface TerminalInstance {
  id: string;
  sessionName: string;
  terminal: any;
  fitAddon: any;
  ws: WebSocket | null;
  connected: boolean;
  resizeObserver: ResizeObserver | null;
  resizeTimeout: ReturnType<typeof setTimeout> | null;
  themeObserver: MutationObserver | null;
  containerEl: HTMLElement;
}

const XTERM_JS_URL = "https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js";
const XTERM_CSS_URL = "https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css";
const FIT_ADDON_URL =
  "https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js";

/** Load xterm.js by fetching source text and executing with AMD disabled. */
async function loadXtermModules(): Promise<{ Terminal: any; FitAddon: any }> {
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
  return {
    Terminal: win.Terminal?.Terminal || win.Terminal,
    FitAddon: win.FitAddon?.FitAddon || win.FitAddon,
  };
}

function loadCSS(href: string): void {
  if (document.querySelector(`link[href="${href}"]`)) return;
  const el = document.createElement("link");
  el.rel = "stylesheet";
  el.href = href;
  document.head.appendChild(el);
}

export class AIPanelConsoleMode {
  private TerminalCtor: any = null;
  private FitAddonCtor: any = null;
  private instances = new Map<string, TerminalInstance>();
  private activeTabId: string | null = null;
  private tabManager = new ConsoleTabManager();
  private hostEl: HTMLElement | null = null;
  private statusEl: HTMLElement | null = null;
  private toolbar: ConsoleToolbarRefs | null = null;
  private recorder: VoiceRecorder | null = null;
  private initialized = false;

  async init(
    hostEl: HTMLElement,
    statusEl: HTMLElement | null,
    toolbar?: ConsoleToolbarRefs,
    tabsListEl?: HTMLElement | null,
  ): Promise<void> {
    if (this.initialized) return;
    this.initialized = true;
    this.hostEl = hostEl;
    this.statusEl = statusEl;
    this.toolbar = toolbar || null;

    loadCSS(XTERM_CSS_URL);

    try {
      const modules = await loadXtermModules();
      this.TerminalCtor = modules.Terminal;
      this.FitAddonCtor = modules.FitAddon;
    } catch (err) {
      console.error("[AIPanelConsole] Failed to load xterm.js:", err);
      return;
    }

    if (!this.TerminalCtor) {
      console.error("[AIPanelConsole] xterm.js Terminal class not available");
      return;
    }

    // Initialize tab manager
    if (tabsListEl) {
      this.tabManager.init(tabsListEl, hostEl, {
        onCreate: (tab) => this.onTabCreate(tab),
        onSwitch: (tab) => this.onTabSwitch(tab),
        onClose: (tab) => this.onTabClose(tab),
      });
      this.tabManager.createTab("T1");
    } else {
      // Fallback: single terminal without tabs
      this.createInstance("default", hostEl);
    }

    // Wire shared toolbar
    this.wireToolbar();

    // Auto-accept for Claude Code CLI prompts (targets active terminal)
    setupAutoAccept({
      getWs: () => this.getActiveWs(),
      getTerminal: () => this.getActiveTerminal(),
    });

    // Project switch: cd if idle, toast if busy (see console-project-switch.ts)
    setupProjectSwitchHandler(
      () => this.getActiveWs(),
      () => this.getActiveTerminal(),
    );
  }

  // --- Tab callbacks ---

  private onTabCreate(tab: ConsoleTab): void {
    this.createInstance(tab.id, tab.containerEl, tab.sessionName);
  }

  private onTabSwitch(tab: ConsoleTab): void {
    this.activeTabId = tab.id;
    // Fit the now-visible terminal after layout settles
    const inst = this.instances.get(tab.id);
    if (inst) {
      setTimeout(() => this.fitInstance(inst), 50);
      this.setStatus(inst.connected ? "connected" : "disconnected");
    }
  }

  private onTabClose(tab: ConsoleTab): void {
    this.destroyInstance(tab.id);
  }

  // --- Instance lifecycle ---

  private async createInstance(
    id: string,
    containerEl: HTMLElement,
    sessionName?: string,
  ): Promise<void> {
    // Wait for web fonts before opening terminal — prevents grid miscalculation
    await document.fonts.ready;

    const terminal = new this.TerminalCtor({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
      theme: this.getTheme(),
      scrollback: 10000,
    });

    terminal.open(containerEl);

    let fitAddon: any = null;
    let resizeObserver: ResizeObserver | null = null;
    let resizeTimeout: ReturnType<typeof setTimeout> | null = null;

    if (this.FitAddonCtor) {
      fitAddon = new this.FitAddonCtor();
      terminal.loadAddon(fitAddon);
      try {
        fitAddon.fit();
      } catch {
        /* hidden */
      }
      // Re-fit after fonts fully load for accurate grid
      document.fonts.ready.then(() => {
        try {
          fitAddon.fit();
        } catch {
          /* */
        }
      });

      // Secondary re-fit after short delay to catch late font rendering
      setTimeout(() => {
        if (fitAddon) {
          try {
            fitAddon.fit();
          } catch {
            /* container may be hidden */
          }
        }
      }, 500);

      let lastObservedW = 0;
      let lastObservedH = 0;
      resizeObserver = new ResizeObserver((entries) => {
        const { width, height } = entries[0].contentRect;
        // Skip if dimensions haven't meaningfully changed (prevents feedback loop)
        if (
          Math.abs(width - lastObservedW) < 2 &&
          Math.abs(height - lastObservedH) < 2
        )
          return;
        lastObservedW = width;
        lastObservedH = height;
        if (resizeTimeout) clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
          try {
            fitAddon.fit();
          } catch {
            /* hidden */
          }
          this.sendResize(inst);
        }, 150);
      });
      resizeObserver.observe(containerEl);
    }

    const inst: TerminalInstance = {
      id,
      sessionName: sessionName || `ai-panel-${id}`,
      terminal,
      fitAddon,
      ws: null,
      connected: false,
      resizeObserver,
      resizeTimeout,
      themeObserver: null,
      containerEl,
    };

    // Forward user input to WebSocket
    terminal.onData((data: string) => {
      if (inst.ws?.readyState === WebSocket.OPEN) inst.ws.send(data);
    });

    // Clipboard, selection, and navigation key handling
    terminal.attachCustomKeyEventHandler((ev: KeyboardEvent) => {
      if (preventNavKeyDefault(ev)) return true;
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

    setupFileDrop(containerEl, inst);
    setupRightClick(containerEl, inst);

    // Context-aware zoom
    registerZoomZone({
      el: containerEl,
      getSize: () => terminal?.options?.fontSize ?? 13,
      setSize: (px) => {
        if (terminal) {
          terminal.options.fontSize = px;
          this.fitInstance(inst);
        }
      },
      min: 8,
      max: 24,
      default: 13,
      storageKey: "scitex-terminal-font-size",
    });

    // Allocation spinner with 90s safety timeout (hides on any non-starting state)
    let _st: ReturnType<typeof setTimeout> | null = null;
    const spinnerOn = () => {
      showAllocationSpinner(containerEl);
      if (_st) clearTimeout(_st);
      _st = setTimeout(() => {
        console.warn(
          "[AIPanelConsole] 90s allocation spinner safety timeout — forcibly hiding spinner",
        );
        _st = null;
        hideAllocationSpinner(containerEl);
      }, 90_000);
    };
    const spinnerOff = () => {
      if (_st) {
        clearTimeout(_st);
        _st = null;
      }
      hideAllocationSpinner(containerEl);
    };
    containerEl.addEventListener("scitex-session-state", ((e: CustomEvent) => {
      const s = e.detail?.state;
      if (s === "allocation_starting" || s === "allocation_recovering")
        spinnerOn();
      else spinnerOff(); // ready, connected, exited, error, allocation_dead, etc.
    }) as EventListener);
    this.observeTheme(inst);

    this.instances.set(id, inst);
    this.activeTabId = id;

    // Connect WebSocket — spinner shows only on allocation_starting state event
    this.connectInstance(inst);
  }

  private destroyInstance(id: string): void {
    const inst = this.instances.get(id);
    if (!inst) return;
    inst.resizeObserver?.disconnect();
    inst.themeObserver?.disconnect();
    if (inst.resizeTimeout) clearTimeout(inst.resizeTimeout);
    inst.ws?.close();
    inst.terminal?.dispose();
    this.instances.delete(id);
  }

  // --- WebSocket ---

  private connectInstance(inst: TerminalInstance): void {
    if (inst.connected) return;
    this.setStatus("connecting");

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const projectId =
      document.querySelector<HTMLElement>(".project-selector-btn")?.dataset
        .activeProjectId || "0";
    const url = `${proto}//${window.location.host}/ws/console/terminal/?project_id=${projectId}&session=${encodeURIComponent(inst.sessionName)}`;

    inst.ws = new WebSocket(url);

    inst.ws.onopen = () => {
      inst.connected = true;
      if (inst.id === this.activeTabId) this.setStatus("connected");
      hideAllocationSpinner(inst.containerEl);
      this.sendResize(inst);
    };

    inst.ws.onmessage = (ev) => {
      const processed = handleOscEscapes(ev.data, inst.containerEl);
      if (processed) inst.terminal.write(processed);
    };

    inst.ws.onerror = () => {
      if (inst.id === this.activeTabId) this.setStatus("error");
      hideAllocationSpinner(inst.containerEl);
    };

    inst.ws.onclose = (ev) => {
      inst.connected = false;
      hideAllocationSpinner(inst.containerEl);
      if (inst.id === this.activeTabId) {
        this.setStatus(ev.code === 1000 ? "disconnected" : "error");
      }
      // Always reconnect — broker keeps shells alive and replays scrollback
      setTimeout(
        () => this.connectInstance(inst),
        ev.code === 1000 ? 1000 : 3000,
      );
    };
  }

  // --- Active tab accessors ---

  getActiveWs(): WebSocket | null {
    if (!this.activeTabId) return null;
    return this.instances.get(this.activeTabId)?.ws ?? null;
  }

  private getActiveTerminal(): any {
    if (!this.activeTabId) return null;
    return this.instances.get(this.activeTabId)?.terminal ?? null;
  }

  // --- Toolbar wiring ---

  private wireToolbar(): void {
    if (!this.toolbar) return;
    const send = (t: string) => {
      const ws = this.getActiveWs();
      if (ws?.readyState === WebSocket.OPEN) ws.send(t);
    };
    const sink = makeImageSink(send);

    if (this.toolbar.cameraBtn && this.toolbar.fileInput) {
      const cam = new WebcamCapture(sink as any, this.toolbar.fileInput);
      this.toolbar.cameraBtn.addEventListener("click", () => void cam.open());
    }
    if (this.toolbar.sketchBtn) {
      const sk = new SketchCanvas(sink as any);
      this.toolbar.sketchBtn.addEventListener("click", () => sk.open());
    }
    if (this.toolbar.micBtn) {
      this.recorder = new VoiceRecorder([], this.toolbar.micBtn);
      this.toolbar.micBtn.addEventListener("click", () => {
        if (this.recorder?.isRecording) this.recorder.stop();
        else
          this.recorder?.start(
            () => getCsrfToken(),
            (t) => send(t),
          );
      });
    }
  }

  // --- Utility ---

  private fitInstance(inst: TerminalInstance): void {
    if (inst.fitAddon) {
      try {
        inst.fitAddon.fit();
        this.sendResize(inst);
      } catch {
        /* container may be hidden */
      }
    }
  }

  private sendResize(inst: TerminalInstance): void {
    if (inst.ws?.readyState === WebSocket.OPEN && inst.terminal)
      inst.ws.send(`resize:${inst.terminal.rows}:${inst.terminal.cols}`);
  }

  private setStatus(
    state: "connecting" | "connected" | "disconnected" | "error",
  ): void {
    if (!this.statusEl) return;
    this.statusEl.classList.remove("connected");
    let icon = this.statusEl.querySelector("i");
    if (!icon) {
      icon = document.createElement("i");
      this.statusEl.prepend(icon);
    }
    let textNode = this.statusEl.lastChild;
    if (!textNode || textNode === icon) {
      textNode = document.createTextNode("");
      this.statusEl.appendChild(textNode);
    }
    const map: Record<string, [string, string, boolean]> = {
      connecting: ["fas fa-circle-notch fa-spin", " Connecting...", false],
      connected: ["fas fa-circle", " Connected", true],
      disconnected: ["fas fa-circle", " Disconnected", false],
      error: ["fas fa-exclamation-circle", " Connection failed", false],
    };
    const [cls, txt, active] = map[state];
    icon.className = cls;
    textNode.textContent = txt;
    if (active) this.statusEl.classList.add("connected");
  }

  private getTheme(): Record<string, string> {
    const s = getComputedStyle(document.documentElement);
    const g = (v: string, fb: string) => s.getPropertyValue(v).trim() || fb;
    const dk = document.documentElement.getAttribute("data-theme") !== "light";
    return {
      background: g("--terminal-bg", dk ? "#0d1117" : "#ffffff"),
      foreground: g("--terminal-fg", dk ? "#c9d1d9" : "#24292f"),
      cursor: g("--terminal-cursor", dk ? "#58a6ff" : "#0969da"),
    };
  }

  private observeTheme(inst: TerminalInstance): void {
    inst.themeObserver = new MutationObserver(() => {
      if (!inst.terminal) return;
      inst.terminal.options.theme = this.getTheme();
    });
    inst.themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
  }

  focus(): void {
    this.getActiveTerminal()?.focus();
  }

  destroy(): void {
    for (const id of this.instances.keys()) this.destroyInstance(id);
  }
}
