/**
 * Mermaid Diagram Renderer — live editor with SVG/PNG export.
 *
 * Dynamically imports mermaid from CDN to avoid bundling the large library.
 * Extracted from render-mmd.html inline <script type="module">.
 */

async function initMermaidRenderer(): Promise<void> {
  const { default: mermaid } =
    await import("https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs");

  mermaid.initialize({
    startOnLoad: false,
    theme: "dark",
    securityLevel: "loose",
  });

  const input = document.getElementById("mermaidInput") as HTMLTextAreaElement;
  const output = document.getElementById("mermaidOutput")!;
  const errorBar = document.getElementById("errorBar")!;

  if (!input || !output) return;

  let renderTimer: ReturnType<typeof setTimeout> | null = null;

  async function renderDiagram(): Promise<void> {
    const syntax = input.value.trim();
    if (!syntax) {
      output.innerHTML =
        '<div class="mermaid-empty-state">Enter Mermaid syntax to see preview</div>';
      errorBar.style.display = "none";
      return;
    }
    try {
      errorBar.style.display = "none";
      const old = document.getElementById("mermaid-diagram");
      if (old) old.remove();
      const { svg } = await mermaid.render("mermaid-diagram", syntax);
      output.innerHTML = svg;
    } catch (error: unknown) {
      errorBar.textContent = (error as Error).message;
      errorBar.style.display = "block";
    }
  }

  // Live render with debounce
  input.addEventListener("input", () => {
    if (renderTimer) clearTimeout(renderTimer);
    renderTimer = setTimeout(renderDiagram, 500);
  });

  document.getElementById("clearBtn")?.addEventListener("click", () => {
    input.value = "";
    output.innerHTML =
      '<div class="mermaid-empty-state">Enter Mermaid syntax to see preview</div>';
    errorBar.style.display = "none";
  });

  document.getElementById("copyBtn")?.addEventListener("click", () => {
    const svg = output.querySelector("svg");
    if (svg) {
      navigator.clipboard.writeText(output.innerHTML);
      const btn = document.getElementById("copyBtn")!;
      btn.textContent = "Copied";
      setTimeout(() => {
        btn.textContent = "Copy SVG";
      }, 1200);
    }
  });

  document.getElementById("downloadSvgBtn")?.addEventListener("click", () => {
    const svg = output.querySelector("svg");
    if (svg) {
      const blob = new Blob([output.innerHTML], { type: "image/svg+xml" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "diagram.svg";
      a.click();
      URL.revokeObjectURL(a.href);
    }
  });

  document.getElementById("downloadPngBtn")?.addEventListener("click", () => {
    const svg = output.querySelector("svg");
    if (svg) {
      const data = new XMLSerializer().serializeToString(svg);
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.width * 2;
        canvas.height = img.height * 2;
        const ctx = canvas.getContext("2d")!;
        ctx.scale(2, 2);
        ctx.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {
          if (!blob) return;
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = "diagram.png";
          a.click();
          URL.revokeObjectURL(a.href);
        });
      };
      img.src =
        "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(data)));
    }
  });

  // Sample content
  input.value = `graph TD
    A[Start] --> B{Is it working?}
    B -->|Yes| C[Great!]
    B -->|No| D[Debug]
    D --> B
    C --> E[End]`;
  renderDiagram();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initMermaidRenderer());
} else {
  initMermaidRenderer();
}
