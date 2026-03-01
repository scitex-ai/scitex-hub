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

  constructor(feed: RepoMonitorFeed) {
    this.feed = feed;
    this.filters = this.loadFromStorage();
  }

  init(): void {
    this.wireGitignoreToggle();
    this.wirePauseToggle();
    this.wireClearButton();
    this.applyButtonStates();
  }

  private wireGitignoreToggle(): void {
    const btn = document.getElementById("repo-monitor-gitignore-toggle");
    if (!btn) return;

    btn.addEventListener("click", () => {
      this.filters.respectGitignore = !this.filters.respectGitignore;
      this.applyGitignoreState(btn);
      this.persist();
      this.notifyChange();
    });
  }

  private applyGitignoreState(btn: HTMLElement): void {
    const icon = btn.querySelector<HTMLElement>("i");
    if (this.filters.respectGitignore) {
      btn.classList.add("active");
      if (icon) {
        icon.className = "fas fa-filter";
      }
    } else {
      btn.classList.remove("active");
      if (icon) {
        icon.className = "fas fa-filter-circle-xmark";
      }
    }
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
    const gitignoreBtn = document.getElementById(
      "repo-monitor-gitignore-toggle",
    );
    const pauseBtn = document.getElementById("repo-monitor-pause-toggle");

    if (gitignoreBtn) this.applyGitignoreState(gitignoreBtn);
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
