/**
 * Discovery App — tab switching for Repositories | Users | Organizations
 */

async function loadDiscoveryTab(tab: string): Promise<void> {
  const tabContent = document.getElementById("discovery-tab-content");
  if (!tabContent) return;

  tabContent.style.opacity = "0.5";

  try {
    const resp = await fetch(
      `/apps/discovery/api/explore/?tab=${encodeURIComponent(tab)}`,
      {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      },
    );
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (!data?.success) throw new Error("API reported success=false");
    tabContent.innerHTML = data.html;
  } catch (err) {
    console.error("[discovery] Failed to load tab:", tab, err);
    // Visible error state — never leave the container silently stale.
    // textContent (not innerHTML): `tab` is DOM-attribute derived.
    const msg = document.createElement("p");
    msg.className = "discovery-empty";
    msg.setAttribute("role", "alert");
    msg.textContent = `Failed to load ${tab} (${String(err)}). Reload the page to retry.`;
    tabContent.replaceChildren(msg);
  } finally {
    tabContent.style.opacity = "1";
  }
}

function initDiscovery(): void {
  document.addEventListener("click", (e: Event) => {
    const target = e.target as HTMLElement;
    const tab = target.closest("[data-discovery-tab]") as HTMLElement | null;
    if (!tab) return;

    e.preventDefault();
    const tabName = tab.getAttribute("data-discovery-tab") || "repositories";

    // Update active tab styling
    document.querySelectorAll(".discovery-tab").forEach((el) => {
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
