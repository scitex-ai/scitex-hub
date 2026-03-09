/**
 * RTD embed viewer for Python Packages docs page.
 * Intercepts ReadTheDocs link clicks and shows the docs in an inline iframe.
 */
(function () {
  const container = document.getElementById(
    "rtd-embed-container",
  ) as HTMLElement | null;
  const iframe = document.getElementById(
    "rtd-embed-iframe",
  ) as HTMLIFrameElement | null;
  const title = document.getElementById(
    "rtd-embed-title",
  ) as HTMLElement | null;
  const extLink = document.getElementById(
    "rtd-embed-external",
  ) as HTMLAnchorElement | null;
  const closeBtn = document.getElementById(
    "rtd-embed-close",
  ) as HTMLElement | null;

  if (!container || !iframe || !title || !extLink || !closeBtn) return;

  const docsContent =
    container.closest(".docs-content") ||
    container.closest("#docs-content-area");

  document
    .querySelectorAll<HTMLAnchorElement>(".pkg-link-docs")
    .forEach((link) => {
      link.addEventListener("click", (e: Event) => {
        e.preventDefault();
        const anchor = e.currentTarget as HTMLAnchorElement;
        const url = anchor.href;
        const card = anchor.closest(".pkg-card");
        const pkgName = card?.querySelector("strong")?.textContent ?? "";

        title.textContent = `${pkgName} — ReadTheDocs`;
        extLink.href = url;
        iframe.src = url;
        container.classList.remove("hidden");
        docsContent?.classList.add("rtd-embed-active");
      });
    });

  closeBtn.addEventListener("click", () => {
    container.classList.add("hidden");
    iframe.src = "";
    docsContent?.classList.remove("rtd-embed-active");
  });
})();
