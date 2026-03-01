/**
 * Repository Monitor Filter Controller
 * Manages filter UI buttons and localStorage persistence
 */

import type { FilterConfig, FilterChangeCallback } from "./types.ts";
import { DEFAULT_FILTER_CONFIG } from "./types.ts";
import type { RepoMonitorFeed } from "./RepoMonitorFeed.ts";

const STORAGE_KEY = "scitex-repo-monitor-filters";

export class RepoMonitorFilter {
  private feed: RepoMonitorFeed;
  private filters: FilterConfig;
  private changeCallbacks: FilterChangeCallback[] = [];
  private paused = false;
  private configPanel: HTMLElement | null = null;

  constructor(feed: RepoMonitorFeed) {
    this.feed = feed;
    this.filters = this.loadFromStorage();
  }

  init(): void {
    this.wireConfigToggle();
    this.wirePauseToggle();
    this.wireClearButton();
    this.applyButtonStates();
  }

  private wireConfigToggle(): void {
    const btn = document.getElementById("repo-monitor-config-toggle");
    if (!btn) return;

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (this.configPanel) {
        this.hideConfigPanel();
      } else {
        this.showConfigPanel(btn);
      }
    });
  }

  private showConfigPanel(anchor: HTMLElement): void {
    this.hideConfigPanel();

    const panel = document.createElement("div");
    panel.className = "repo-monitor-config-panel";
    panel.addEventListener("click", (e) => e.stopPropagation());

    const title = document.createElement("div");
    title.className = "rmc-title";
    title.textContent = "Filter Patterns";
    panel.appendChild(title);

    const desc = document.createElement("div");
    desc.className = "rmc-desc";
    desc.textContent = "One glob pattern per line (e.g. *.pyc, __pycache__/*)";
    panel.appendChild(desc);

    // Gitignore toggle (checkbox)
    const gitignoreRow = document.createElement("label");
    gitignoreRow.className = "rmc-checkbox-row";
    const gitignoreCheck = document.createElement("input");
    gitignoreCheck.type = "checkbox";
    gitignoreCheck.checked = this.filters.respectGitignore;
    gitignoreRow.appendChild(gitignoreCheck);
    gitignoreRow.appendChild(document.createTextNode(" Respect .gitignore"));
    panel.appendChild(gitignoreRow);

    // Blacklist textarea
    const blackLabel = document.createElement("label");
    blackLabel.className = "rmc-label";
    blackLabel.textContent = "Exclude patterns:";
    panel.appendChild(blackLabel);

    const blackInput = document.createElement("textarea");
    blackInput.className = "rmc-textarea";
    blackInput.rows = 4;
    blackInput.placeholder = "*.pyc\n__pycache__/*\n.git/*";
    blackInput.value = this.filters.blacklistPatterns.join("\n");
    panel.appendChild(blackInput);

    // Whitelist textarea
    const whiteLabel = document.createElement("label");
    whiteLabel.className = "rmc-label";
    whiteLabel.textContent = "Include only (empty = all):";
    panel.appendChild(whiteLabel);

    const whiteInput = document.createElement("textarea");
    whiteInput.className = "rmc-textarea";
    whiteInput.rows = 3;
    whiteInput.placeholder = "*.py\n*.ts\n*.html";
    whiteInput.value = this.filters.whitelistPatterns.join("\n");
    panel.appendChild(whiteInput);

    // Apply button
    const applyBtn = document.createElement("button");
    applyBtn.className = "rmc-apply";
    applyBtn.textContent = "Apply";
    applyBtn.addEventListener("click", () => {
      this.filters.respectGitignore = gitignoreCheck.checked;
      this.filters.blacklistPatterns = this.parseLines(blackInput.value);
      this.filters.whitelistPatterns = this.parseLines(whiteInput.value);
      this.persist();
      this.notifyChange();
      this.hideConfigPanel();
    });
    panel.appendChild(applyBtn);

    // Position below the anchor
    const monitorArea = document.getElementById("ws-repo-monitor");
    if (monitorArea) {
      monitorArea.appendChild(panel);
    } else {
      anchor.parentElement?.appendChild(panel);
    }

    this.configPanel = panel;
    anchor.classList.add("active");

    // Close on outside click
    const closeHandler = (e: MouseEvent) => {
      if (!panel.contains(e.target as Node) && e.target !== anchor) {
        this.hideConfigPanel();
        document.removeEventListener("mousedown", closeHandler);
      }
    };
    setTimeout(() => document.addEventListener("mousedown", closeHandler), 0);
  }

  private hideConfigPanel(): void {
    if (this.configPanel) {
      this.configPanel.remove();
      this.configPanel = null;
    }
    document
      .getElementById("repo-monitor-config-toggle")
      ?.classList.remove("active");
  }

  private parseLines(text: string): string[] {
    return text
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
  }

  private wirePauseToggle(): void {
    const btn = document.getElementById("repo-monitor-pause-toggle");
    if (!btn) return;

    btn.addEventListener("click", () => {
      this.paused = !this.paused;
      this.applyPauseState(btn);
      this.notifyChange();
    });
  }

  private applyPauseState(btn: HTMLElement): void {
    const icon = btn.querySelector<HTMLElement>("i");
    if (this.paused) {
      btn.classList.add("active");
      if (icon) icon.className = "fas fa-play";
    } else {
      btn.classList.remove("active");
      if (icon) icon.className = "fas fa-pause";
    }
  }

  private wireClearButton(): void {
    const btn = document.getElementById("repo-monitor-clear");
    if (!btn) return;
    btn.addEventListener("click", () => {
      this.feed.clear();
    });
  }

  private applyButtonStates(): void {
    const pauseBtn = document.getElementById("repo-monitor-pause-toggle");
    if (pauseBtn) this.applyPauseState(pauseBtn);
  }

  getFilters(): FilterConfig {
    return { ...this.filters };
  }

  isPaused(): boolean {
    return this.paused;
  }

  onFilterChange(callback: FilterChangeCallback): void {
    this.changeCallbacks.push(callback);
  }

  private notifyChange(): void {
    this.changeCallbacks.forEach((cb) => cb(this.getFilters()));
  }

  private persist(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.filters));
    } catch {
      // ignore quota errors
    }
  }

  private loadFromStorage(): FilterConfig {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return { ...DEFAULT_FILTER_CONFIG, ...JSON.parse(raw) };
    } catch {
      // ignore
    }
    return { ...DEFAULT_FILTER_CONFIG };
  }
}
