/**
 * Sidebar Context Menu — right-click on module items for app-specific actions.
 */

let activeMenu: HTMLElement | null = null;

export function initSidebarContextMenu(): void {
  const sidebar = document.getElementById("workspace-sidebar");
  if (!sidebar) return;

  // Right-click on module items
  sidebar.addEventListener("contextmenu", (e) => {
    const item = (e.target as HTMLElement).closest<HTMLElement>(
      ".sidebar-item[data-module]",
    );
    if (!item) return;

    e.preventDefault();
    const moduleName = item.getAttribute("data-module") || "";
    const moduleLabel =
      item.querySelector(".sidebar-label")?.textContent?.trim() || moduleName;
    showContextMenu(e as MouseEvent, moduleName, moduleLabel, item);
  });

  // Close on any click
  document.addEventListener("click", closeContextMenu);
  document.addEventListener("contextmenu", () => closeContextMenu());
}

function showContextMenu(
  e: MouseEvent,
  moduleName: string,
  moduleLabel: string,
  item: HTMLElement,
): void {
  closeContextMenu();

  const menu = document.createElement("div");
  menu.className = "sidebar-context-menu";

  const actions = [
    {
      icon: "fas fa-external-link-alt",
      label: `Open ${moduleLabel}`,
      action: () => {
        const href = item.getAttribute("href") || `/apps/${moduleName}/`;
        window.location.href = href;
      },
    },
    {
      icon: "fas fa-arrow-up",
      label: "Move up",
      action: () => moveModule(item, "up"),
    },
    {
      icon: "fas fa-arrow-down",
      label: "Move down",
      action: () => moveModule(item, "down"),
    },
    { divider: true },
    {
      icon: "fas fa-eye-slash",
      label: "Hide from sidebar",
      action: () => hideModule(moduleName, item),
      danger: true,
    },
  ];

  actions.forEach((act) => {
    if ("divider" in act && act.divider) {
      const hr = document.createElement("div");
      hr.className = "sidebar-ctx-divider";
      menu.appendChild(hr);
      return;
    }
    const btn = document.createElement("button");
    btn.className = "sidebar-ctx-item";
    if ("danger" in act && act.danger) btn.classList.add("danger");
    btn.innerHTML = `<i class="${act.icon}"></i><span>${act.label}</span>`;
    btn.addEventListener("click", () => {
      closeContextMenu();
      if ("action" in act && act.action) act.action();
    });
    menu.appendChild(btn);
  });

  // Position near cursor
  menu.style.position = "fixed";
  menu.style.left = `${e.clientX}px`;
  menu.style.top = `${e.clientY}px`;
  menu.style.zIndex = "1000";

  document.body.appendChild(menu);
  activeMenu = menu;

  // Adjust if overflows viewport
  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) {
    menu.style.left = `${window.innerWidth - rect.width - 8}px`;
  }
  if (rect.bottom > window.innerHeight) {
    menu.style.top = `${window.innerHeight - rect.height - 8}px`;
  }
}

function closeContextMenu(): void {
  if (activeMenu) {
    activeMenu.remove();
    activeMenu = null;
  }
}

function moveModule(item: HTMLElement, direction: "up" | "down"): void {
  const sibling =
    direction === "up" ? item.previousElementSibling : item.nextElementSibling;
  if (!sibling || !sibling.classList.contains("sidebar-item")) return;

  if (direction === "up") {
    item.parentElement?.insertBefore(item, sibling);
  } else {
    item.parentElement?.insertBefore(sibling, item);
  }

  // Persist order
  const order = Array.from(
    item.parentElement?.querySelectorAll<HTMLElement>(
      ".sidebar-item[data-module]",
    ) || [],
  ).map((el) => el.getAttribute("data-module") || "");

  if (window._moduleReorder) {
    window._moduleReorder.postModuleOrder(order);
    window._moduleReorder.syncTabBar(order);
  }
}

function hideModule(moduleName: string, item: HTMLElement): void {
  item.style.display = "none";
  // Could call API to disable module, but for now just visual hide
  console.log(`[context-menu] Hidden module: ${moduleName}`);
}
