/**
 * Workspace Sidebar — pane switching, collapse/expand, mobile drawer.
 *
 * Manages the Claude.ai-inspired single-pane layout:
 * - Core panes (chat, console, files, editor) switch client-side
 * - Module panes navigate via URL (Django routing)
 * - Sidebar expand/collapse persisted in localStorage
 * - Mobile drawer with backdrop + swipe-to-close
 */

const STORAGE_KEY_SIDEBAR = "ws-sidebar-state";
const STORAGE_KEY_PANE = "ws-active-pane";

type PaneId = "chat" | "console" | "files" | "editor" | "module";

class WorkspaceSidebar {
  private sidebar: HTMLElement | null = null;
  private sidebarInner: HTMLElement | null = null;
  private backdrop: HTMLElement | null = null;
  private toggleBtn: HTMLElement | null = null;
  private hamburger: HTMLElement | null = null;
  private items: NodeListOf<HTMLElement> | null = null;
  private panes: NodeListOf<HTMLElement> | null = null;
  private currentPane: PaneId = "chat";
  private touchStartX = 0;

  init(): void {
    this.sidebar = document.getElementById("workspace-sidebar");
    if (!this.sidebar) return;

    this.sidebarInner = document.getElementById("sidebar-inner");
    this.backdrop = document.getElementById("sidebar-backdrop");
    this.toggleBtn = document.getElementById("sidebar-toggle");
    this.hamburger = document.getElementById("mobile-hamburger");
    this.items = this.sidebar.querySelectorAll<HTMLElement>(".sidebar-item");
    this.panes = document.querySelectorAll<HTMLElement>(".workspace-pane");

    this.restoreState();
    this.bindEvents();
    this.activateInitialPane();
  }

  /* ── State persistence ──────────────────────────────────── */

  private restoreState(): void {
    if (!this.sidebar) return;

    // Restore sidebar expand/collapse
    const saved = localStorage.getItem(STORAGE_KEY_SIDEBAR);
    if (saved === "collapsed") {
      this.sidebar.setAttribute("data-sidebar-state", "collapsed");
    } else {
      this.sidebar.setAttribute("data-sidebar-state", "expanded");
    }
  }

  private activateInitialPane(): void {
    // Check data-initial-pane (set by /chat/, /console/, /files/ routes)
    const initialPane = document.body.getAttribute("data-initial-pane");
    if (initialPane && this.isCorePaneId(initialPane)) {
      this.switchPane(initialPane as PaneId, false);
      return;
    }

    // Check URL hash (#chat, #console, #files)
    const hash = window.location.hash.replace("#", "");
    if (hash && this.isCorePaneId(hash)) {
      this.switchPane(hash as PaneId, false);
      return;
    }

    // If we're on a module page, activate "module" pane
    // Detect module from URL path as primary source (more reliable)
    const path = window.location.pathname;
    const urlModule = path.match(/^\/apps\/([^/]+)\//)?.[1] || null;
    const trackModule =
      urlModule || document.body.getAttribute("data-track-module");

    if (trackModule && trackModule !== "files") {
      this.switchPane("module", false);
      // Highlight the active module in sidebar
      this.highlightModuleItem(trackModule);
    } else {
      // Restore last active core pane, default to chat
      const saved = localStorage.getItem(STORAGE_KEY_PANE) as PaneId | null;
      const paneId = saved && this.isCorePaneId(saved) ? saved : "chat";
      this.switchPane(paneId, false);
    }
  }

  private isCorePaneId(id: string): id is PaneId {
    return ["chat", "console", "editor", "module"].includes(id);
  }

  /* ── Event binding ──────────────────────────────────────── */

  private bindEvents(): void {
    // Sidebar item clicks
    this.items?.forEach((item) => {
      item.addEventListener("click", (e) => this.onItemClick(e, item));
    });

    // Toggle expand/collapse
    this.toggleBtn?.addEventListener("click", () => this.toggleSidebar());

    // Mobile hamburger
    this.hamburger?.addEventListener("click", () => this.openDrawer());

    // Backdrop click closes drawer
    this.backdrop?.addEventListener("click", () => this.closeDrawer());

    // Swipe to close drawer
    this.sidebarInner?.addEventListener("touchstart", (e) => {
      this.touchStartX = e.touches[0].clientX;
    });
    this.sidebarInner?.addEventListener("touchend", (e) => {
      const dx = e.changedTouches[0].clientX - this.touchStartX;
      if (dx < -60) this.closeDrawer();
    });

    // Keyboard shortcuts (Alt+key)
    document.addEventListener("keydown", (e) => this.onKeyDown(e));

    // Hash change (browser back/forward)
    window.addEventListener("hashchange", () => {
      const hash = window.location.hash.replace("#", "");
      if (hash && this.isCorePaneId(hash) && hash !== this.currentPane) {
        this.switchPane(hash as PaneId, false);
      }
    });

    // New chat button
    document
      .getElementById("sidebar-new-chat")
      ?.addEventListener("click", () => {
        this.switchPane("chat", true);
        const newChatBtn = document.querySelector<HTMLElement>(
          ".stx-shell-ai-new-chat",
        );
        newChatBtn?.click();
      });

    // Project selector dropdown toggle
    this.initProjectDropdown();
  }

  private initProjectDropdown(): void {
    const toggle = document.getElementById("sidebar-project-toggle");
    const dropdown = document.getElementById("sidebar-project-dropdown");
    if (!toggle || !dropdown) return;

    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("open");
    });

    // Close on outside click
    document.addEventListener("click", () => {
      dropdown.classList.remove("open");
    });

    dropdown.addEventListener("click", (e) => {
      e.stopPropagation();
    });
  }

  /* ── Pane switching ─────────────────────────────────────── */

  private onItemClick(e: Event, item: HTMLElement): void {
    const paneId = item.getAttribute("data-pane") as PaneId | null;
    if (!paneId) return;

    const moduleName = item.getAttribute("data-module");

    if (paneId === "module" && moduleName) {
      // Module items: switch to module pane + load content via AJAX
      e.preventDefault();
      this.switchPane("module", true);
      this.highlightModuleItem(moduleName);
      this.loadModuleContent(moduleName, item);
      this.closeDrawer();
      return;
    }

    // Core panes: prevent default and switch client-side
    e.preventDefault();
    this.switchPane(paneId, true);
    this.closeDrawer();
  }

  private switchPane(paneId: PaneId, persist: boolean): void {
    if (!this.panes) return;

    this.currentPane = paneId;

    // Hide all panes, show selected
    this.panes.forEach((pane) => {
      const id = pane.getAttribute("data-pane");
      pane.classList.toggle("active", id === paneId);
    });

    // Move AI panel to the active Chat/Console pane
    if (paneId === "chat" || paneId === "console") {
      this.moveAiPanel(paneId);
      this.switchAiPanelMode(paneId === "chat" ? "chat" : "console");
    }

    // Force-uncollapse any inner panels (clear old localStorage collapsed state)
    this.forceExpandPanels(paneId);

    // Update sidebar active state for core panes
    this.items?.forEach((item) => {
      const itemPane = item.getAttribute("data-pane");
      const itemModule = item.getAttribute("data-module");

      if (paneId !== "module") {
        item.classList.toggle("active", itemPane === paneId && !itemModule);
      }
    });

    // Persist core pane selection and update URL
    if (persist && paneId !== "module") {
      localStorage.setItem(STORAGE_KEY_PANE, paneId);
      // Map pane IDs to URL paths
      const paneUrls: Record<string, string> = {
        chat: "/chat/",
        console: "/console/",
        editor: "/files/",
      };
      const targetUrl = paneUrls[paneId] || `/#${paneId}`;
      history.pushState({ pane: paneId }, "", targetUrl);
    }

    // Dispatch event for other components to react
    document.dispatchEvent(
      new CustomEvent("workspace-pane-changed", { detail: { pane: paneId } }),
    );
  }

  private highlightModuleItem(moduleName: string): void {
    this.items?.forEach((item) => {
      const itemModule = item.getAttribute("data-module");
      if (itemModule) {
        item.classList.toggle("active", itemModule === moduleName);
      } else if (item.getAttribute("data-pane") !== "module") {
        item.classList.remove("active");
      }
    });
  }

  /* ── AJAX module loading ─────────────────────────────────── */

  private async loadModuleContent(
    moduleName: string,
    item: HTMLElement,
  ): Promise<void> {
    const pane = document.getElementById("main-content");
    if (!pane) return;

    // If already showing this module, skip
    const current = pane.getAttribute("data-app-accent");
    if (current === moduleName && !pane.classList.contains("switching")) {
      return;
    }

    pane.classList.add("switching");

    try {
      const resp = await fetch(`/apps/workspace/content/${moduleName}/`, {
        headers: { "X-Workspace-Shell": "1" },
        credentials: "same-origin",
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const html = await resp.text();
      pane.innerHTML = html;

      // Re-execute inline scripts
      pane.querySelectorAll("script").forEach((old) => {
        if (old.type === "importmap") {
          old.remove();
          return;
        }
        const replacement = document.createElement("script");
        Array.from(old.attributes).forEach((attr) =>
          replacement.setAttribute(attr.name, attr.value),
        );
        replacement.textContent = old.textContent;
        old.replaceWith(replacement);
      });

      // Update accent and URL
      pane.setAttribute("data-app-accent", moduleName);
      pane.style.removeProperty("--app-accent-color");
      const href = item.getAttribute("href") || `/apps/${moduleName}/`;
      history.pushState({ module: moduleName }, "", href);

      document.dispatchEvent(
        new CustomEvent("workspace:module-injected", {
          detail: { module: moduleName },
        }),
      );
    } catch (err) {
      console.error("[sidebar] Failed to load module:", moduleName, err);
      // Fallback: navigate normally
      const href = item.getAttribute("href") || `/apps/${moduleName}/`;
      location.href = href;
    } finally {
      pane.classList.remove("switching");
    }
  }

  /* ── Force expand inner panels ───────────────────────────── */

  private forceExpandPanels(paneId: string): void {
    const pane = document.getElementById(`pane-${paneId}`);
    if (!pane) return;

    // Remove collapsed class from all inner sidebars
    pane.querySelectorAll<HTMLElement>(".stx-shell-sidebar").forEach((el) => {
      el.classList.remove("collapsed");
      el.removeAttribute("aria-hidden");
    });
  }

  /* ── AI panel DOM movement ───────────────────────────────── */

  private moveAiPanel(targetPane: "chat" | "console"): void {
    const aiContainer = document.getElementById("ai-panel-container");
    const targetEl = document.getElementById(`pane-${targetPane}`);
    if (!aiContainer || !targetEl) return;

    // Move the AI panel into the target pane
    targetEl.appendChild(aiContainer);
  }

  /* ── AI panel mode switching ──────────────────────────────── */

  private switchAiPanelMode(mode: "chat" | "console"): void {
    // Click the mode toggle button in the AI panel
    const modeBtn = document.querySelector<HTMLElement>(
      `.stx-shell-ai-mode-btn[data-mode="${mode}"]`,
    );
    if (modeBtn && !modeBtn.classList.contains("active")) {
      modeBtn.click();
    }
  }

  /* ── Sidebar toggle ─────────────────────────────────────── */

  private toggleSidebar(): void {
    if (!this.sidebar) return;
    const current = this.sidebar.getAttribute("data-sidebar-state");
    const next = current === "collapsed" ? "expanded" : "collapsed";
    this.sidebar.setAttribute("data-sidebar-state", next);
    localStorage.setItem(STORAGE_KEY_SIDEBAR, next);
  }

  /* ── Mobile drawer ──────────────────────────────────────── */

  private openDrawer(): void {
    this.sidebar?.classList.add("drawer-open");
    document.body.style.overflow = "hidden";
  }

  private closeDrawer(): void {
    this.sidebar?.classList.remove("drawer-open");
    document.body.style.overflow = "";
  }

  /* ── Keyboard shortcuts ─────────────────────────────────── */

  private onKeyDown(e: KeyboardEvent): void {
    if (!e.altKey || e.ctrlKey || e.metaKey) return;

    const key = e.key.toLowerCase();
    let pane: PaneId | null = null;

    switch (key) {
      case "a":
        pane = "chat";
        break;
      case "t":
        pane = "console";
        break;
      case "e":
        pane = "editor";
        break;
      default:
        return;
    }

    if (pane) {
      e.preventDefault();
      this.switchPane(pane, true);
    }
  }
}

// Auto-init on DOM ready
const sidebar = new WorkspaceSidebar();
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => sidebar.init());
} else {
  sidebar.init();
}

export { WorkspaceSidebar };
