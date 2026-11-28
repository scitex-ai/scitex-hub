// File editor functionality

(function () {
  "use strict";

  function showEdit(): void {
    const editorTextarea = document.getElementById(
      "editorTextarea",
    ) as HTMLElement | null;
    const previewContainer = document.getElementById(
      "previewContainer",
    ) as HTMLElement | null;
    const editBtn = document.getElementById("editBtn") as HTMLElement | null;
    const previewBtn = document.getElementById(
      "previewBtn",
    ) as HTMLElement | null;

    if (editorTextarea && previewContainer && editBtn && previewBtn) {
      editorTextarea.style.display = "block";
      previewContainer.style.display = "none";
      editBtn.classList.add("active");
      previewBtn.classList.remove("active");
    }
  }

  function showPreview(): void {
    const editorTextarea = document.getElementById(
      "editorTextarea",
    ) as HTMLTextAreaElement | null;
    const previewContainer = document.getElementById(
      "previewContainer",
    ) as HTMLElement | null;
    const editBtn = document.getElementById("editBtn") as HTMLElement | null;
    const previewBtn = document.getElementById(
      "previewBtn",
    ) as HTMLElement | null;

    if (editorTextarea && previewContainer && editBtn && previewBtn) {
      const content = editorTextarea.value;

      // Access marked library from window object (defined in global.d.ts)
      // The file may have been written by another collaborator: the preview
      // only ever receives sanitised markup (DOMPurify is loaded globally by
      // global_body_scripts.html). Without the sanitiser, show text only.
      const purify = (window as any).DOMPurify;
      if (
        window.marked &&
        typeof window.marked.parse === "function" &&
        purify &&
        typeof purify.sanitize === "function"
      ) {
        const html = window.marked.parse(content);
        previewContainer.innerHTML = purify.sanitize(html);
      } else if (window.marked && typeof window.marked.parse === "function") {
        previewContainer.textContent = content;
      } else {
        console.error("marked library not found");
        previewContainer.innerHTML =
          "<p>Error: Markdown parser not available</p>";
      }

      editorTextarea.style.display = "none";
      previewContainer.style.display = "block";
      editBtn.classList.remove("active");
      previewBtn.classList.add("active");
    }
  }

  // Expose functions to window object for HTML onclick handlers
  (window as any).showEdit = showEdit;
  (window as any).showPreview = showPreview;
})();
