/**
 * Organization Profile — filter repos/apps by name.
 */
(function () {
  const input = document.getElementById(
    "org-repo-filter",
  ) as HTMLInputElement | null;
  if (!input) return;
  input.addEventListener("input", function () {
    const q = this.value.toLowerCase();
    document
      .querySelectorAll<HTMLElement>(".org-filterable-item")
      .forEach(function (card) {
        const name = (card.dataset.name || "").toLowerCase();
        card.classList.toggle("hub-hidden", q !== "" && !name.includes(q));
      });
  });
})();
