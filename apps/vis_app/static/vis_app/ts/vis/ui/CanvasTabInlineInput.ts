/**
 * Inline input handling for canvas tab rename and new tab creation
 */

import type { CanvasTabManager } from "./CanvasTabManager";

function createHintTooltip(): HTMLElement {
  const hint = document.createElement("div");
  hint.className = "rename-hint-tooltip";
  hint.textContent = "Space → _";
  hint.style.cssText =
    "display:none;position:absolute;background:#6c757d;color:white;padding:2px 6px;border-radius:3px;font-size:11px;z-index:9999;";
  return hint;
}

function setupSpaceToUnderscore(
  input: HTMLInputElement,
  hint: HTMLElement,
): void {
  input.addEventListener("beforeinput", (e: InputEvent) => {
    if (e.data?.includes(" ")) {
      e.preventDefault();
      const start = input.selectionStart || 0;
      const end = input.selectionEnd || 0;
      const replaced = e.data.replace(/\s+/g, "_");
      input.value =
        input.value.slice(0, start) + replaced + input.value.slice(end);
      input.setSelectionRange(start + replaced.length, start + replaced.length);
      hint.style.display = "block";
      setTimeout(() => (hint.style.display = "none"), 1000);
    }
  });

  input.oninput = () => {
    if (input.value.includes(" ")) {
      const pos = input.selectionStart || 0;
      input.value = input.value.replace(/\s+/g, "_");
      input.setSelectionRange(pos, pos);
      hint.style.display = "block";
      setTimeout(() => (hint.style.display = "none"), 1000);
    }
  };
}

export function startInlineRename(
  itemEl: HTMLElement,
  tabId: string,
  labelEl: HTMLElement,
  mgr: CanvasTabManager,
): void {
  const currentName = labelEl.textContent || "";
  const input = document.createElement("input");
  input.type = "text";
  input.className = "figure-rename-input";
  input.value = currentName;
  const hint = createHintTooltip();

  labelEl.style.display = "none";
  itemEl.insertBefore(input, labelEl.nextSibling);
  itemEl.appendChild(hint);
  input.focus();
  input.select();

  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    mgr.renameTab(tabId, input.value.trim() || currentName);
    input.remove();
    hint.remove();
    labelEl.style.display = "";
  };

  setupSpaceToUnderscore(input, hint);
  input.onblur = finish;
  input.onkeydown = (e) => {
    e.stopPropagation();
    if (e.key === "Enter") {
      e.preventDefault();
      finish();
    } else if (e.key === "Escape") {
      e.preventDefault();
      input.value = currentName;
      finish();
    }
  };
}

export async function showInlineNewTabInput(
  mgr: CanvasTabManager,
  closeDropdown: () => void,
): Promise<void> {
  const menu = document.getElementById("figure-dropdown-menu");
  if (!menu) return;

  document.getElementById("figure-dropdown-container")?.classList.add("open");
  if (menu.querySelector(".inline-new-tab-input")) {
    (menu.querySelector(".inline-new-tab-input") as HTMLInputElement)?.focus();
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "figure-dropdown-item inline-new-tab-wrapper";

  const icon = document.createElement("i");
  icon.className = "fas fa-paint-brush";
  wrapper.appendChild(icon);

  const input = document.createElement("input");
  input.type = "text";
  input.className = "inline-new-tab-input figure-rename-input";
  const defaultName = mgr._generateUniqueFigureName();
  input.value = defaultName;
  input.placeholder = defaultName;

  const hint = createHintTooltip();
  wrapper.appendChild(input);
  wrapper.appendChild(hint);
  menu.appendChild(wrapper);
  input.focus();
  input.select();

  let done = false;
  const finish = async () => {
    if (done) return;
    done = true;
    const name = input.value.trim() || defaultName;
    wrapper.remove();
    const bundlePath = await mgr.createFigzBundleOnBackend(name);
    const newTabId = mgr.createTab(name, bundlePath || undefined);
    mgr.switchToTab(newTabId);
    closeDropdown();
  };

  const cancel = () => {
    if (!done) {
      done = true;
      wrapper.remove();
    }
  };
  setupSpaceToUnderscore(input, hint);

  input.onblur = () =>
    setTimeout(() => {
      if (document.activeElement !== input) finish();
    }, 100);
  input.onkeydown = (e) => {
    e.stopPropagation();
    if (e.key === "Enter") {
      e.preventDefault();
      finish();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancel();
    }
  };
}
