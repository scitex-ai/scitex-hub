/**
 * Dev Install — install/uninstall app repos from Hub as personal dev apps.
 *
 * Uses event delegation on data-action="dev-install" and data-action="dev-uninstall"
 * buttons. No inline onclick handlers.
 */

function getCsrf(): string {
  const meta = document.querySelector(
    "[name=csrfmiddlewaretoken]",
  ) as HTMLInputElement | null;
  if (meta) return meta.value;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

function handleDevInstall(btn: HTMLButtonElement): void {
  const owner = btn.dataset.owner;
  const repo = btn.dataset.repo;
  if (!owner || !repo) return;

  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Installing...';

  fetch("/apps/api/dev/install/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrf(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ owner, repo }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        btn.innerHTML = '<i class="fas fa-check"></i> Installed';
        btn.classList.add("btn-success");
      } else {
        btn.innerHTML =
          '<i class="fas fa-times"></i> ' + (data.error || "Failed");
        btn.disabled = false;
      }
    })
    .catch(() => {
      btn.innerHTML = '<i class="fas fa-download"></i> Dev Install';
      btn.disabled = false;
    });
}

function handleDevUninstall(btn: HTMLButtonElement): void {
  const owner = btn.dataset.owner;
  const repo = btn.dataset.repo;
  if (!owner || !repo) return;

  btn.disabled = true;

  fetch(`/apps/api/dev/${owner}/${repo}/uninstall/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrf(),
      "Content-Type": "application/json",
    },
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        const card = btn.closest(".ap-card-dev");
        if (card) card.remove();
        const section = document.querySelector(".apps-dev-section");
        if (section && !section.querySelector(".ap-card-dev")) section.remove();
      } else {
        btn.disabled = false;
      }
    })
    .catch(() => {
      btn.disabled = false;
    });
}

/** Event delegation — listen on document for dev install/uninstall clicks. */
document.addEventListener("click", (e: Event) => {
  const target = e.target as HTMLElement;
  const btn = target.closest("[data-action]") as HTMLButtonElement | null;
  if (!btn) return;

  const action = btn.dataset.action;
  if (action === "dev-install") {
    handleDevInstall(btn);
  } else if (action === "dev-uninstall") {
    handleDevUninstall(btn);
  }
});
