/**
 * Reads the active project slug from the global header project selector.
 *
 * The server always resolves paths using request.user — the client only
 * supplies the slug so the server can look up the right project for the
 * authenticated user (same permissions as the user themselves).
 */
export function readActiveProjectSlug(): string {
  // 1. After a JS-driven switch, the selected item gets the 'active' class
  const byActive = document.querySelector<HTMLElement>(
    ".dropdown-project-item.active[data-project-slug]",
  );
  if (byActive) return byActive.getAttribute("data-project-slug") ?? "";

  // 2. On initial page load, Django renders the check mark as visible
  const byCheck = Array.from(
    document.querySelectorAll<HTMLElement>(
      ".dropdown-project-item[data-project-slug]",
    ),
  ).find((el) => {
    const check = el.querySelector<HTMLElement>(".project-item-check");
    return check && check.style.display !== "none";
  });
  if (byCheck) return byCheck.getAttribute("data-project-slug") ?? "";

  // 3. Fall back to the first available project (single-project users)
  const first = document.querySelector<HTMLElement>(
    ".dropdown-project-item[data-project-slug]",
  );
  return first?.getAttribute("data-project-slug") ?? "";
}
