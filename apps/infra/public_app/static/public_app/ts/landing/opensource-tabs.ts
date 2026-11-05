/** Shared SDK tab markup; only the selected repository group occupies space. */
export function initOpenSourceTabs(root: ParentNode = document): void {
  root.querySelectorAll<HTMLElement>('[data-oss-tabs]').forEach((tablist) => {
    if (tablist.dataset.ossTabsMounted) return;
    const tabs = [...tablist.querySelectorAll<HTMLButtonElement>('[role="tab"]')];
    const panels = tabs.map((tab) => root.querySelector<HTMLElement>(`#${tab.getAttribute('aria-controls')}`));
    if (!tabs.length || panels.some((panel) => !panel)) return;

    const select = (index: number, focus = false) => {
      tabs.forEach((tab, i) => {
        const active = i === index;
        tab.setAttribute('aria-selected', String(active));
        tab.tabIndex = active ? 0 : -1;
        panels[i]!.hidden = !active;
      });
      if (focus) tabs[index].focus();
    };
    tabs.forEach((tab, index) => {
      panels[index]!.setAttribute('role', 'tabpanel');
      panels[index]!.setAttribute('aria-labelledby', tab.id);
      panels[index]!.tabIndex = 0;
      const heading = panels[index]!.querySelector('h3');
      if (heading) heading.hidden = true;
      tab.addEventListener('click', () => select(index));
      tab.addEventListener('keydown', (event) => {
        let next: number;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = tabs.length - 1;
        else return;
        event.preventDefault();
        select(next, true);
      });
    });
    select(0);
    tablist.hidden = false;
    tablist.dataset.ossTabsMounted = 'true';
  });
}

