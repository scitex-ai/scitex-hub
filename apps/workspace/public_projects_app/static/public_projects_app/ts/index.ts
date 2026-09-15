/**
 * Public Projects App — tab switching for Projects | Users | Organizations
 * (the Projects tab keeps the API key "repositories"; only its label changed).
 */

async function loadDiscoveryTab(tab: string): Promise<void> {
  const tabContent = document.getElementById("public-projects-tab-content");
  if (!tabContent) return;

  tabContent.style.opacity = "0.5";

  try {
    const resp = await fetch(
      `/apps/public-projects/api/explore/?tab=${encodeURIComponent(tab)}`,
      {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      },
    );
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (!data?.success) throw new Error("API reported success=false");
    tabContent.innerHTML = data.html;
  } catch (err) {
    console.error("[public_projects] Failed to load tab:", tab, err);
    // Visible error state — never leave the container silently stale.
    // textContent (not innerHTML): `tab` is DOM-attribute derived.
    const msg = document.createElement("p");
    msg.className = "public-projects-empty";
    msg.setAttribute("role", "alert");
    const label = tab === "repositories" ? "projects" : tab;
    msg.textContent = `Failed to load ${label} (${String(err)}). Reload the page to retry.`;
    tabContent.replaceChildren(msg);
  } finally {
    tabContent.style.opacity = "1";
  }
}

function initDiscovery(): void {
  document.addEventListener("click", (e: Event) => {
    const target = e.target as HTMLElement;
    const tab = target.closest("[data-public-projects-tab]") as HTMLElement | null;
    if (!tab) return;

    e.preventDefault();
    const tabName = tab.getAttribute("data-public-projects-tab") || "repositories";

    // Update active tab styling
    document.querySelectorAll(".public-projects-tab").forEach((el) => {
      el.classList.remove("active");
    });
    tab.classList.add("active");

    loadDiscoveryTab(tabName);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDiscovery);
} else {
  initDiscovery();
}

export {};
