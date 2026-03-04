/**
 * Dev Install — install/uninstall app repos from Hub as personal dev apps.
 *
 * Uses event delegation on data-action="dev-install" and data-action="dev-uninstall"
 * buttons. No inline onclick handlers.
 *
 * On successful install, injects a nav item into the sidebar immediately
 * so the user sees the app tab without a page reload.
 */

function getCsrf(): string {
  const meta = document.querySelector(
    "[name=csrfmiddlewaretoken]",
  ) as HTMLInputElement | null;
  if (meta) return meta.value;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

/** Inject a new nav item into the apps sidebar after dev install. */
function injectSidebarNavItem(
  moduleName: string,
  label: string,
  icon: string,
): void {
  const nav = document.querySelector("#ws-app-selector") as HTMLElement | null;
  if (!nav) return;

  const link = document.createElement("a");
  link.href = `/${moduleName}/`;
  link.className = "selector-nav-item ws-apps-nav-item module-tab-btn";
  link.dataset.module = moduleName;
  link.setAttribute("aria-label", label);
  link.title = label;
  link.dataset.moduleAccent = moduleName;

  // Icon + DEV badge overlay
  link.innerHTML =
    `<span class="dev-icon-wrap">` +
    `<i class="${icon}"></i>` +
    `<span class="dev-badge">DEV</span>` +
    `</span>` +
    `<span class="selector-nav-label ws-apps-nav-label">${label}</span>`;

  nav.appendChild(link);

  // Update data-workspace-modules list
  const current = nav.dataset.workspaceModules || "";
  nav.dataset.workspaceModules = current
    ? `${current},${moduleName}`
    : moduleName;
}

/** Remove a nav item from the sidebar on dev uninstall. */
function removeSidebarNavItem(owner: string, repo: string): void {
  const moduleName = `dev__${owner}__${repo}`;
  const nav = document.querySelector("#ws-app-selector") as HTMLElement | null;
  if (!nav) return;

  const item = nav.querySelector(
    `[data-module="${moduleName}"]`,
  ) as HTMLElement | null;
  if (item) item.remove();

  // Update data-workspace-modules list
  const current = nav.dataset.workspaceModules || "";
  nav.dataset.workspaceModules = current
    .split(",")
    .filter((m) => m !== moduleName)
    .join(",");
}

function handleDevInstall(btn: HTMLButtonElement): void {
  const owner = btn.dataset.owner;
  const repo = btn.dataset.repo;
  if (!owner || !repo) return;

  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Installing...';

  fetch("/apps/api/dev/install/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrf(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ owner, repo }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        btn.innerHTML = '<i class="fas fa-check"></i> Installed';
        btn.classList.remove("repo-action-btn-dev");
        btn.classList.add("repo-action-btn-installed");
        injectSidebarNavItem(
          data.module_name,
          data.label,
          data.icon || "fas fa-puzzle-piece",
        );
      } else {
        btn.innerHTML =
          '<i class="fas fa-times"></i> ' + (data.error || "Failed");
        btn.disabled = false;
      }
    })
    .catch(() => {
      btn.innerHTML = '<i class="fas fa-download"></i> Dev Install';
      btn.disabled = false;
    });
}

function handleDevUninstall(btn: HTMLButtonElement): void {
  const owner = btn.dataset.owner;
  const repo = btn.dataset.repo;
  if (!owner || !repo) return;

  btn.disabled = true;

  fetch(`/apps/api/dev/${owner}/${repo}/uninstall/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrf(),
      "Content-Type": "application/json",
    },
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        // Remove from sidebar
        removeSidebarNavItem(owner, repo);
        // Remove card from Apps browse page
        const card = btn.closest(".ap-card-dev");
        if (card) card.remove();
        const section = document.querySelector(".apps-dev-section");
        if (section && !section.querySelector(".ap-card-dev")) section.remove();
      } else {
        btn.disabled = false;
      }
    })
    .catch(() => {
      btn.disabled = false;
    });
}

/** Event delegation — listen on document for dev install/uninstall clicks. */
document.addEventListener("click", (e: Event) => {
  const target = e.target as HTMLElement;
  const btn = target.closest("[data-action]") as HTMLButtonElement | null;
  if (!btn) return;

  const action = btn.dataset.action;
  if (action === "dev-install") {
    handleDevInstall(btn);
  } else if (action === "dev-uninstall") {
    handleDevUninstall(btn);
  }
});
