/** Mobile account navigation uses only the original server-rendered options. */

export function localSettingsPagePath(raw: string, origin: string): string | null {
  if (
    !raw.startsWith("/") ||
    raw.startsWith("//") ||
    /[\\\x00-\x20\x7f]/.test(raw)
  ) {
    return null;
  }
  try {
    const base = new URL(origin);
    const target = new URL(raw, base.origin);
    if (
      !/^https?:$/.test(target.protocol) ||
      target.origin !== base.origin ||
      // A normalized path must stay local when location parses it again.
      target.pathname.startsWith("//")
    ) {
      return null;
    }
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return null;
  }
}

export function createSettingsDestinationResolver(
  options: readonly HTMLOptionElement[],
  origin: string,
): (option: HTMLOptionElement | null, group: string) => string | null {
  const allowed = new WeakMap<
    HTMLOptionElement,
    { raw: string; path: string; group: string | undefined }
  >();
  for (const option of options) {
    const path = localSettingsPagePath(option.value, origin);
    if (path !== null) {
      allowed.set(option, {
        raw: option.value,
        path,
        group: option.dataset.group,
      });
    }
  }
  return (option, group) => {
    if (!option || option.hidden) return null;
    const destination = allowed.get(option);
    if (
      !destination ||
      destination.raw !== option.value ||
      destination.group !== group ||
      destination.group !== option.dataset.group
    ) {
      return null;
    }
    return destination.path;
  };
}

export function initSettingsNavigation(): void {
  const groupElement = document.getElementById("settings-cascade-group");
  const pageElement = document.getElementById("settings-cascade-page");
  if (
    !(groupElement instanceof HTMLSelectElement) ||
    !(pageElement instanceof HTMLSelectElement)
  ) {
    return;
  }
  const group = groupElement;
  const page = pageElement;
  if (page.dataset.settingsNavigationMounted === "true") return;
  page.dataset.settingsNavigationMounted = "true";

  const options = Array.from(page.options);
  const resolveDestination = createSettingsDestinationResolver(
    options,
    window.location.origin,
  );

  function filter(): void {
    for (const option of options) {
      option.hidden = option.dataset.group !== group.value;
    }
    const visible = options.filter((option) => !option.hidden);
    if (!visible.some((option) => option.selected) && visible.length) {
      visible[0].selected = true;
    }
  }

  group.addEventListener("change", filter);
  page.addEventListener("change", () => {
    const destination = resolveDestination(
      page.selectedOptions.item(0),
      group.value,
    );
    if (destination !== null) window.location.assign(destination);
  });
  filter();
  page
    .closest(".settings-nav-cascade")
    ?.setAttribute("data-settings-navigation-ready", "true");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSettingsNavigation, {
    once: true,
  });
} else {
  initSettingsNavigation();
}
