/**
 * Hub Settings Nav — inline section loading for account settings panel.
 *
 * The settings panel (#hub-account-settings) lives outside .hub-browse-container,
 * so its nav-link clicks must be intercepted here, before the container guard.
 */

export function handleSettingsNavClick(
  target: HTMLElement,
  hubMain: HTMLElement,
  e: Event,
): boolean {
  const settingsNav = target.closest(
    "#hub-account-settings a.settings-nav-item",
  ) as HTMLAnchorElement | null;
  if (!settingsNav) return false;

  e.preventDefault();
  e.stopPropagation();
  const href = settingsNav.getAttribute("href");
  if (!href) return true;

  // Update active state
  hubMain
    .querySelectorAll("#hub-account-settings a.settings-nav-item")
    .forEach((el) => el.classList.remove("active"));
  settingsNav.classList.add("active");

  // Fetch section content inline
  const contentEl = hubMain.querySelector<HTMLElement>(
    "#hub-settings-section-content",
  );
  if (contentEl)
    contentEl.innerHTML =
      '<div style="padding:1rem;opacity:0.5">Loading…</div>';

  fetch(href, { headers: { "X-Requested-With": "XMLHttpRequest" } })
    .then((r) => r.text())
    .then((html) => {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      const extracted =
        doc.querySelector("main.settings-content") ||
        doc.querySelector(".settings-content") ||
        doc.querySelector("main");
      if (contentEl && extracted) {
        contentEl.innerHTML = extracted.innerHTML;
      } else if (contentEl) {
        contentEl.innerHTML = html;
      }
    })
    .catch(() => {
      if (contentEl)
        contentEl.innerHTML =
          '<div style="padding:1rem;color:red">Failed to load section.</div>';
    });

  return true;
}
