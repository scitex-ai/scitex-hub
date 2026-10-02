/** Dismiss the welcome without creating or selecting a project. */
export function initFirstLoginWelcome(root: ParentNode = document): void {
  const welcome = root.querySelector<HTMLElement>("[data-first-login-welcome]");
  const close = welcome?.querySelector<HTMLButtonElement>("[data-first-login-dismiss]");
  if (!welcome || !close || welcome.dataset.dismissInitialized === "true") return;
  welcome.dataset.dismissInitialized = "true";

  const username = document.body.dataset.currentUsername;
  const key = document.body.dataset.userAuthenticated === "true" && username
    ? `scitex-first-login-welcome-dismissed:${username}`
    : null;
  try {
    if (key && localStorage.getItem(key) === "true") welcome.hidden = true;
  } catch {
    // Blocked browser storage must still allow the current card to close.
  }

  const dismiss = (event: Event): void => {
    event.preventDefault();
    event.stopPropagation();
    welcome.hidden = true;
    try {
      if (key) localStorage.setItem(key, "true");
    } catch {
      // The card closes even when the browser cannot remember the preference.
    }
    const apps = document.getElementById("launcher-grid");
    if (apps) {
      apps.tabIndex = -1;
      apps.focus({ preventScroll: true });
    }
  };
  close.addEventListener("click", dismiss);
  welcome.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key === "Escape" && !event.defaultPrevented) dismiss(event);
  });
}
