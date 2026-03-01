/**
 * Repository Monitor - Orchestrator
 * Wires together client, feed, filter, and resizer components
 *
 * Usage:
 * ```typescript
 * import { initRepoMonitor } from '@shared/components/repo-monitor';
 *
 * initRepoMonitor({
 *   projectId: "42",
 *   username: "test-user",
 *   slug: "my-project",
 * });
 * ```
 */

import { RepoMonitorClient } from "./RepoMonitorClient.ts";
import { RepoMonitorFeed } from "./RepoMonitorFeed.ts";
import { RepoMonitorFilter } from "./RepoMonitorFilter.ts";
import { VerticalSplitResizer } from "./VerticalSplitResizer.ts";
import type { MonitorConfig } from "./types.ts";

export function initRepoMonitor(config: MonitorConfig): void {
  const feedContainer = document.getElementById("repo-monitor-feed");
  const monitorArea = document.getElementById("ws-repo-monitor");
  const resizerEl = document.getElementById("repo-monitor-resizer");
  const treeArea = document.querySelector(
    ".ws-worktree-tree-area",
  ) as HTMLElement | null;
  const headerEl = document.getElementById("repo-monitor-header");

  if (!feedContainer || !monitorArea || !resizerEl || !treeArea) {
    console.warn("[RepoMonitor] Missing required DOM elements — init skipped");
    return;
  }

  const client = new RepoMonitorClient(config.projectId);
  const feed = new RepoMonitorFeed(feedContainer);
  const filter = new RepoMonitorFilter(feed);
  const resizer = new VerticalSplitResizer(resizerEl, treeArea, monitorArea);

  // Wire events
  client.onEvent((event) => feed.addEvent(event));
  filter.onFilterChange((filters) => client.reconfigure(filters));

  // Header click toggles collapse (toolbar buttons handled independently)
  headerEl?.addEventListener("click", (e) => {
    if ((e.target as HTMLElement).closest(".repo-monitor-toolbar")) return;
    monitorArea.classList.toggle("collapsed");
    resizer.restoreState();

    if (monitorArea.classList.contains("collapsed")) {
      client.pause();
    } else {
      client.resume();
    }
  });

  // Connect and initialize
  client.connect();
  filter.init();
  resizer.restoreState();
}

// Named re-exports for consumers that need individual classes
export { RepoMonitorClient } from "./RepoMonitorClient.ts";
export { RepoMonitorFeed } from "./RepoMonitorFeed.ts";
export { RepoMonitorFilter } from "./RepoMonitorFilter.ts";
export { VerticalSplitResizer } from "./VerticalSplitResizer.ts";
export type { FsEvent, FilterConfig, MonitorConfig } from "./types.ts";
