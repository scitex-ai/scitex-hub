/**
 * Hub Me Tab — project selector dropdown with fuzzy search.
 */

const HIDDEN = "hub-hidden";

// ── Fuzzy match helpers ────────────────────────────────────────────────────

/** Returns match score > 0 if needle is a subsequence of haystack.
 *  Consecutive matches score higher. */
function fuzzyScore(needle: string, haystack: string): number {
  if (!needle) return 1;
  const n = needle.toLowerCase();
  const h = haystack.toLowerCase();
  let ni = 0;
  let score = 0;
  let consecutive = 0;
  for (let hi = 0; hi < h.length && ni < n.length; hi++) {
    if (n[ni] === h[hi]) {
      ni++;
      consecutive++;
      score += consecutive;
    } else {
      consecutive = 0;
    }
  }
  return ni === n.length ? score : 0;
}

/** Wrap matched characters in <mark> tags for highlight display. */
function fuzzyHighlight(needle: string, text: string): string {
  if (!needle) return escHtml(text);
  const n = needle.toLowerCase();
  const t = text.toLowerCase();
  let result = "";
  let ni = 0;
  for (let i = 0; i < text.length; i++) {
    if (ni < n.length && n[ni] === t[i]) {
      result += `<mark>${escHtml(text[i])}</mark>`;
      ni++;
    } else {
      result += escHtml(text[i]);
    }
  }
  return result;
}

function escHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Filter and highlight project items by fuzzy query. */
function filterProjects(menu: HTMLElement, query: string): void {
  const items = menu.querySelectorAll<HTMLElement>(".hub-me-project-item");
  const noResults = menu.querySelector<HTMLElement>(".hub-project-no-results");
  let visibleCount = 0;

  items.forEach((item) => {
    const name = item.dataset.projectName || "";
    const slug = item.dataset.projectSlug || "";
    const score = Math.max(fuzzyScore(query, name), fuzzyScore(query, slug));

    if (score > 0 || !query) {
      item.classList.remove(HIDDEN);
      const nameEl = item.querySelector<HTMLElement>(".project-item-name");
      if (nameEl) {
        nameEl.innerHTML = query ? fuzzyHighlight(query, name) : escHtml(name);
      }
      visibleCount++;
    } else {
      item.classList.add(HIDDEN);
    }
  });

  if (noResults) {
    noResults.classList.toggle(HIDDEN, visibleCount > 0);
  }
}

// ── Dropdown handlers ──────────────────────────────────────────────────────

/** Handle toggle click on .hub-me-project-selector-btn. Returns true if handled. */
export function handleMeProjectDropdown(
  target: HTMLElement,
  e: Event,
): boolean {
  const btn = target.closest(
    ".hub-me-project-selector-btn",
  ) as HTMLElement | null;
  if (!btn) return false;

  e.preventDefault();
  e.stopPropagation();

  const menu = btn.parentElement?.querySelector(
    ".hub-me-project-selector-menu",
  ) as HTMLElement | null;
  if (!menu) return true;

  const wasHidden = menu.classList.contains(HIDDEN);
  menu.classList.toggle(HIDDEN);

  if (wasHidden) {
    // Menu just opened — focus search and reset filter
    const searchInput = menu.querySelector<HTMLInputElement>(
      ".hub-project-search-input",
    );
    if (searchInput) {
      searchInput.value = "";
      filterProjects(menu, "");
      setTimeout(() => searchInput.focus(), 30);

      if (!searchInput.dataset.listenerAttached) {
        searchInput.dataset.listenerAttached = "1";
        searchInput.addEventListener("input", () =>
          filterProjects(menu, searchInput.value),
        );
        searchInput.addEventListener("keydown", (ke) => {
          if (ke.key === "Escape") {
            menu.classList.add(HIDDEN);
            ke.stopPropagation();
          } else if (ke.key === "Enter") {
            const first = menu.querySelector<HTMLElement>(
              `.hub-me-project-item:not(.${HIDDEN})`,
            );
            if (first) first.click();
            ke.preventDefault();
            ke.stopPropagation();
          }
        });
      }
    }
  }

  return true;
}

/** Handle project item click in .hub-me-project-selector-menu. Returns true if handled. */
export function handleMeProjectSelect(target: HTMLElement, e: Event): boolean {
  const item = target.closest(".hub-me-project-item") as HTMLElement | null;
  if (!item?.dataset.projectId) return false;

  e.preventDefault();
  e.stopPropagation();

  const pid = item.dataset.projectId;
  const pname = item.dataset.projectName || "";
  const pslug = item.dataset.projectSlug || "";
  const powner = item.dataset.projectOwner || "";

  // Close menu
  const menu = item.closest(
    ".hub-me-project-selector-menu",
  ) as HTMLElement | null;
  if (menu) menu.classList.add(HIDDEN);

  // Update active name display in selector button
  document
    .querySelectorAll<HTMLElement>(".hub-me-project-active-name")
    .forEach((el) => {
      el.textContent = pname;
    });

  // Update check marks
  document
    .querySelectorAll<HTMLElement>(".hub-me-project-item .project-item-check")
    .forEach((check) => {
      const parentItem = check.closest(
        ".hub-me-project-item",
      ) as HTMLElement | null;
      if (parentItem?.dataset.projectId === pid) {
        check.classList.remove(HIDDEN);
      } else {
        check.classList.add(HIDDEN);
      }
    });

  // Update tab label to slug only — NO navigation
  const projectsTab = document.querySelector(
    '[data-hub-mode="projects"]',
  ) as HTMLElement | null;
  if (projectsTab) {
    const label = projectsTab.querySelector(
      ".hub-mode-project-label",
    ) as HTMLElement | null;
    if (label) {
      label.textContent = pslug || "—";
    }
    projectsTab.dataset.projectId = pid;
  }

  // Use canonical project-switch API (single source of truth)
  const csrfToken =
    document
      .querySelector("[name=csrfmiddlewaretoken]")
      ?.getAttribute("value") ||
    document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
    "";
  fetch("/api/project/switch/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: JSON.stringify({ project_id: pid }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        // Dispatch canonical sync event so all other selectors update
        window.dispatchEvent(
          new CustomEvent("scitex:project-switched", {
            detail: {
              projectId: pid,
              projectSlug: pslug,
              ownerUsername: powner,
              projectName: pname,
              source: "hub-me-tab",
            },
          }),
        );
      } else {
        console.error("project switch failed:", data.error);
      }
    })
    .catch((err) => console.error("project switch failed:", err));

  return true;
}

/** Filter repository cards in the Me tab by fuzzy query. */
export function filterRepoCards(query: string): void {
  const cards = document.querySelectorAll<HTMLElement>(
    ".hub-repos-section .hub-project-card-link",
  );
  const noResults = document.getElementById("hub-repo-no-results");
  let visible = 0;

  cards.forEach((card) => {
    const name = card.dataset.projectName || "";
    const slug = card.dataset.projectSlug || "";
    const desc =
      card.querySelector(".project-card-body p")?.textContent?.trim() || "";
    const topics = Array.from(card.querySelectorAll(".topic-tag"))
      .map((t) => t.textContent || "")
      .join(" ");
    const haystack = `${name} ${slug} ${desc} ${topics}`;
    const score = fuzzyScore(query, haystack);

    if (score > 0 || !query) {
      card.classList.remove(HIDDEN);
      const nameEl = card.querySelector<HTMLElement>(".hub-project-name-link");
      if (nameEl) {
        nameEl.innerHTML = query ? fuzzyHighlight(query, name) : escHtml(name);
      }
      visible++;
    } else {
      card.classList.add(HIDDEN);
    }
  });

  if (noResults)
    noResults.classList.toggle(HIDDEN, visible > 0 || !cards.length);
}

/** Bind Ctrl+K to focus the repo filter input. */
export function initRepoFilterShortcut(): void {
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.ctrlKey && !e.altKey && !e.shiftKey && e.key === "k") {
      const filter = document.getElementById(
        "hub-repo-filter",
      ) as HTMLInputElement | null;
      if (filter) {
        e.preventDefault();
        filter.focus();
        filter.select();
      }
    }
  });
}

/** Close all Me tab dropdowns (call on outside click). */
export function closeMeProjectDropdowns(): void {
  document
    .querySelectorAll<HTMLElement>(".hub-me-project-selector-menu")
    .forEach((menu) => {
      menu.classList.add(HIDDEN);
    });
}
