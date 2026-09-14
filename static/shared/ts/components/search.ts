/** Header command palette: grouped jump-to results from /api/search/. */

import {
  isOpenPaletteShortcut,
  nextActiveIndex,
  paletteActionForKey,
} from "./_search-navigation";

interface SearchResult {
  title: string;
  subtitle: string;
  url: string;
  icon: string;
}

interface SearchGroup {
  key: string;
  label: string;
  results: SearchResult[];
}

interface SearchResponse {
  groups: SearchGroup[];
}

const TYPING_DEBOUNCE_MS = 120;

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
  );
}

function buildResultLink(
  result: SearchResult,
  optionId: string,
): HTMLAnchorElement {
  const link = document.createElement("a");
  link.className = "search-modal-result-item";
  link.id = optionId;
  link.href = result.url;
  link.setAttribute("role", "option");
  link.setAttribute("aria-selected", "false");

  const icon = document.createElement("i");
  icon.className = `search-modal-result-icon ${result.icon}`;
  icon.setAttribute("aria-hidden", "true");

  const content = document.createElement("span");
  content.className = "search-modal-result-content";
  const title = document.createElement("span");
  title.className = "search-modal-result-title";
  title.textContent = result.title;
  content.append(title);
  if (result.subtitle) {
    const subtitle = document.createElement("span");
    subtitle.className = "search-modal-result-subtitle";
    subtitle.textContent = result.subtitle;
    content.append(subtitle);
  }

  link.append(icon, content);
  return link;
}

function initializeHeaderSearch(): void {
  const modal = document.getElementById("search-modal");
  const input = document.getElementById(
    "search-modal-input",
  ) as HTMLInputElement | null;
  const resultsBox = document.getElementById("search-modal-results");
  if (!modal || !input || !resultsBox) return;
  // The header is its own stacking context; at body level the palette sits above the site dock.
  document.body.append(modal);

  const endpoint = modal.dataset.endpoint ?? "/api/search/";
  const noResultsText = modal.dataset.noResultsText ?? "";
  const hintText = resultsBox.textContent?.trim() ?? "";

  let resultLinks: HTMLAnchorElement[] = [];
  let activeIndex = -1;
  let typingTimer: number | undefined;
  let pendingRequest: AbortController | null = null;
  let openerElement: HTMLElement | null = null;

  function showMessage(text: string): void {
    const message = document.createElement("p");
    message.className = "search-modal-hint";
    message.textContent = text;
    resultsBox!.replaceChildren(message);
    resultLinks = [];
    setActiveIndex(-1);
  }

  function setActiveIndex(index: number): void {
    resultLinks[activeIndex]?.classList.remove("is-active");
    resultLinks[activeIndex]?.setAttribute("aria-selected", "false");
    activeIndex = index;
    const activeLink = resultLinks[activeIndex];
    if (activeLink) {
      activeLink.classList.add("is-active");
      activeLink.setAttribute("aria-selected", "true");
      activeLink.scrollIntoView({ block: "nearest" });
      input!.setAttribute("aria-activedescendant", activeLink.id);
    } else {
      input!.removeAttribute("aria-activedescendant");
    }
  }

  function renderGroups(groups: SearchGroup[]): void {
    if (groups.length === 0) {
      showMessage(noResultsText);
      return;
    }
    const fragment = document.createDocumentFragment();
    resultLinks = [];
    for (const group of groups) {
      const section = document.createElement("div");
      section.className = "search-modal-group";
      section.setAttribute("role", "group");
      const heading = document.createElement("div");
      heading.className = "search-modal-section-header";
      heading.id = `search-group-${group.key}`;
      heading.textContent = group.label;
      section.setAttribute("aria-labelledby", heading.id);
      section.append(heading);
      for (const result of group.results) {
        const link = buildResultLink(
          result,
          `search-option-${resultLinks.length}`,
        );
        resultLinks.push(link);
        section.append(link);
      }
      fragment.append(section);
    }
    resultsBox!.replaceChildren(fragment);
    activeIndex = -1;
    setActiveIndex(0);
  }

  async function fetchResults(query: string): Promise<void> {
    pendingRequest?.abort();
    pendingRequest = new AbortController();
    try {
      const response = await fetch(
        `${endpoint}?q=${encodeURIComponent(query)}`,
        {
          headers: { Accept: "application/json" },
          signal: pendingRequest.signal,
        },
      );
      if (!response.ok) return;
      const data: SearchResponse = await response.json();
      if (input!.value.trim() === query) renderGroups(data.groups);
    } catch (error) {
      if ((error as Error).name !== "AbortError")
        console.error("Header search failed:", error);
    }
  }

  function openPalette(opener: HTMLElement | null): void {
    if (!modal!.hidden) return;
    openerElement = opener;
    modal!.hidden = false;
    input!.setAttribute("aria-expanded", "true");
    document.body.classList.add("search-modal-open");
    input!.focus();
  }

  function closePalette(): void {
    if (modal!.hidden) return;
    modal!.hidden = true;
    pendingRequest?.abort();
    window.clearTimeout(typingTimer);
    input!.value = "";
    input!.setAttribute("aria-expanded", "false");
    document.body.classList.remove("search-modal-open");
    showMessage(hintText);
    openerElement?.focus();
  }

  document
    .querySelectorAll<HTMLElement>("[data-search-open]")
    .forEach((opener) => {
      opener.addEventListener("click", () => openPalette(opener));
    });
  modal
    .querySelectorAll<HTMLElement>("[data-search-close]")
    .forEach((closer) => {
      closer.addEventListener("click", closePalette);
    });

  input.addEventListener("input", () => {
    window.clearTimeout(typingTimer);
    const query = input.value.trim();
    if (!query) {
      pendingRequest?.abort();
      showMessage(hintText);
      return;
    }
    typingTimer = window.setTimeout(
      () => fetchResults(query),
      TYPING_DEBOUNCE_MS,
    );
  });

  modal.addEventListener("keydown", (event: KeyboardEvent) => {
    const action = paletteActionForKey(event.key);
    if (!action) return;
    if (action === "close") {
      event.preventDefault();
      closePalette();
      return;
    }
    if (action === "open") {
      const activeLink = resultLinks[activeIndex];
      if (activeLink && event.target === input) {
        event.preventDefault();
        window.location.assign(activeLink.href);
      }
      return;
    }
    if ((action === "first" || action === "last") && event.target === input)
      return;
    event.preventDefault();
    setActiveIndex(nextActiveIndex(activeIndex, action, resultLinks.length));
  });

  // Capture phase: "/" must win over page handlers that navigate to /search/.
  window.addEventListener(
    "keydown",
    (event: KeyboardEvent) => {
      if (
        event.key !== "/" ||
        !isOpenPaletteShortcut(event, isEditableTarget(event.target))
      )
        return;
      event.preventDefault();
      event.stopPropagation();
      openPalette(document.activeElement as HTMLElement | null);
    },
    true,
  );

  // Bubble phase: page-specific Ctrl/Cmd+K handlers run first and may claim the key.
  window.addEventListener("keydown", (event: KeyboardEvent) => {
    if (
      event.key === "/" ||
      !isOpenPaletteShortcut(event, isEditableTarget(event.target))
    )
      return;
    event.preventDefault();
    openPalette(document.activeElement as HTMLElement | null);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeHeaderSearch);
} else {
  initializeHeaderSearch();
}
