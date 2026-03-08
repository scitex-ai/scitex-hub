/**
 * Hub URL — GitHub-style pushState URL management.
 * Updates browser URL bar during SPA navigation.
 */

/** Get current branch name from the DOM. */
export function getBranch(): string {
  return (
    document.getElementById("current-branch-name")?.textContent?.trim() ||
    "main"
  );
}

/** Push a project-scoped URL: /<owner>/<slug>/<suffix> */
export function pushProjectUrl(suffix?: string): void {
  const data = (window as any).SCITEX_PROJECT_DATA;
  if (!data?.owner || !data?.slug) return;
  const base = `/${data.owner}/${data.slug}`;
  const url = suffix ? `${base}/${suffix}` : `${base}/`;
  if (location.pathname !== url) {
    history.pushState(
      { view: "project", owner: data.owner, slug: data.slug },
      "",
      url,
    );
  }
}

/** Push the dashboard (current project) URL. */
export function pushDashboardUrl(): void {
  history.pushState({ view: "dashboard" }, "", "/");
}

/** Push the explore URL. */
export function pushExploreUrl(): void {
  if (location.pathname !== "/explore/") {
    history.pushState({ view: "explore" }, "", "/explore/");
  }
}

/** Push the Me (user profile) URL. */
export function pushMeUrl(username: string): void {
  const url = `/${encodeURIComponent(username)}/`;
  if (location.pathname !== url) {
    history.pushState({ view: "me", username }, "", url);
  }
}
