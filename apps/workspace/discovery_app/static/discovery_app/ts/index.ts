/**
 * Discovery App — tab switching for Repositories | Users | Organizations
 */

async function loadDiscoveryTab(tab: string): Promise<void> {
  const tabContent = document.getElementById("discovery-tab-content");
  if (!tabContent) return;

  tabContent.style.opacity = "0.5";

  const resp = await fetch(
    `/apps/discovery/api/explore/?tab=${encodeURIComponent(tab)}`,
    {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    },
  );

  if (resp.ok) {
    const data = await resp.json();
    if (data?.success) tabContent.innerHTML = data.html;
  }

  tabContent.style.opacity = "1";
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
