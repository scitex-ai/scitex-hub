/**
 * Sketch Canvas — freehand drawing tool for AI chat.
 *
 * Opens as a modal overlay, supports pen/eraser/color/width,
 * exports PNG for multimodal LLM vision input.
 * Uses raw HTML5 Canvas + Pointer Events API (no dependencies).
 */

import type { ImageInputManager } from "./image-input";

function getSketchColors(): string[] {
  const isDark =
    document.documentElement.getAttribute("data-theme") !== "light";
  return isDark
    ? [
        "#ffffff",
        "#ef4444",
        "#f59e0b",
        "#22c55e",
        "#3b82f6",
        "#8b5cf6",
        "#ec4899",
        "#6b7280",
      ]
    : [
        "#1a1a2e",
        "#dc2626",
        "#d97706",
        "#16a34a",
        "#2563eb",
        "#7c3aed",
        "#db2777",
        "#4b5563",
      ];
}
const WIDTHS = [2, 5, 10];
const WIDTH_LABELS = ["Thin", "Med", "Thick"];

type Tool = "pen" | "eraser";

export class SketchCanvas {
  private overlay: HTMLElement | null = null;
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private imageInput: ImageInputManager;

  private tool: Tool = "pen";
  private color = "#ffffff";
  private lineWidth = WIDTHS[1];
  private drawing = false;

  constructor(imageInput: ImageInputManager) {
    this.imageInput = imageInput;
  }

  open(): void {
    if (this.overlay) return;
    this.overlay = this.buildUI();
    document.body.appendChild(this.overlay);
  }

  close(): void {
    this.overlay?.remove();
    this.overlay = null;
    this.canvas = null;
    this.ctx = null;
  }

  /* ── UI Construction ────────────────────────────────────────── */

  private buildUI(): HTMLElement {
    const overlay = document.createElement("div");
    overlay.className = "scitex-sketch-overlay";

    const panel = document.createElement("div");
    panel.className = "scitex-sketch-panel";
    overlay.appendChild(panel);

    // Toolbar
    const toolbar = document.createElement("div");
    toolbar.className = "scitex-sketch-toolbar";
    panel.appendChild(toolbar);

    // Tool buttons
    const penBtn = this.toolBtn("Pen", "fas fa-pen", () => this.setTool("pen"));
    const eraserBtn = this.toolBtn("Eraser", "fas fa-eraser", () =>
      this.setTool("eraser"),
    );
    penBtn.classList.add("active");
    toolbar.append(penBtn, eraserBtn);

    // Separator
    toolbar.appendChild(this.sep());

    // Color swatches — theme-aware
    const colors = getSketchColors();
    this.color = colors[0];
    for (const c of colors) {
      const swatch = document.createElement("button");
      swatch.className = "scitex-sketch-color";
      swatch.style.background = c;
      if (c === this.color) swatch.classList.add("active");
      swatch.addEventListener("click", () => {
        toolbar
          .querySelectorAll(".scitex-sketch-color")
          .forEach((s) => s.classList.remove("active"));
        swatch.classList.add("active");
        this.color = c;
        this.setTool("pen");
        toolbar
          .querySelectorAll(".scitex-sketch-tool")
          .forEach((b) =>
            b.classList.toggle("active", b.textContent?.trim() === "Pen"),
          );
      });
      toolbar.appendChild(swatch);
    }

    // Separator
    toolbar.appendChild(this.sep());

    // Width buttons
    for (let i = 0; i < WIDTHS.length; i++) {
      const btn = document.createElement("button");
      btn.className = "scitex-sketch-width";
      btn.textContent = WIDTH_LABELS[i];
      if (WIDTHS[i] === this.lineWidth) btn.classList.add("active");
      btn.addEventListener("click", () => {
        toolbar
          .querySelectorAll(".scitex-sketch-width")
          .forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.lineWidth = WIDTHS[i];
      });
      toolbar.appendChild(btn);
    }

    // Canvas — sized to fill most of the viewport
    this.canvas = document.createElement("canvas");
    this.canvas.className = "scitex-sketch-canvas";
    this.canvas.width = 1200;
    this.canvas.height = 800;
    panel.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d")!;
    this.ctx.fillStyle = this.canvasBg();
    this.ctx.fillRect(0, 0, 1200, 800);
    this.bindDrawing(this.canvas);

    // Action buttons
    const actions = document.createElement("div");
    actions.className = "scitex-sketch-actions";

    const clearBtn = document.createElement("button");
    clearBtn.className = "scitex-sketch-btn";
    clearBtn.textContent = "Clear";
    clearBtn.addEventListener("click", () => this.clearCanvas());

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "scitex-sketch-btn";
    cancelBtn.textContent = "Cancel";
    cancelBtn.addEventListener("click", () => this.close());

    const doneBtn = document.createElement("button");
    doneBtn.className = "scitex-sketch-btn scitex-sketch-btn-primary";
    doneBtn.textContent = "Done";
    doneBtn.addEventListener("click", () => this.done());

    actions.append(clearBtn, cancelBtn, doneBtn);
    panel.appendChild(actions);

    // Close on overlay click (outside panel)
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) this.close();
    });

    // Esc to close
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        this.close();
        document.removeEventListener("keydown", onKey);
      }
    };
    document.addEventListener("keydown", onKey);

    return overlay;
  }

  private toolBtn(
    label: string,
    icon: string,
    onClick: () => void,
  ): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.className = "scitex-sketch-tool";
    btn.innerHTML = `<i class="${icon}"></i> ${label}`;
    btn.addEventListener("click", () => {
      const toolbar = btn.parentElement!;
      toolbar
        .querySelectorAll(".scitex-sketch-tool")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      onClick();
    });
    return btn;
  }

  private sep(): HTMLElement {
    const el = document.createElement("span");
    el.className = "scitex-sketch-sep";
    return el;
  }

  /* ── Drawing ────────────────────────────────────────────────── */

  private bindDrawing(canvas: HTMLCanvasElement): void {
    canvas.addEventListener("pointerdown", (e) => this.startDraw(e));
    canvas.addEventListener("pointermove", (e) => this.draw(e));
    canvas.addEventListener("pointerup", () => this.endDraw());
    canvas.addEventListener("pointerleave", () => this.endDraw());
    // Prevent scrolling on touch
    canvas.style.touchAction = "none";
  }

  private startDraw(e: PointerEvent): void {
    this.drawing = true;
    const ctx = this.ctx!;
    ctx.beginPath();
    const { x, y } = this.coords(e);
    ctx.moveTo(x, y);
  }

  private draw(e: PointerEvent): void {
    if (!this.drawing || !this.ctx) return;
    const ctx = this.ctx;
    const { x, y } = this.coords(e);
    ctx.lineWidth = this.lineWidth;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    if (this.tool === "eraser") {
      ctx.globalCompositeOperation = "destination-out";
      ctx.strokeStyle = "rgba(0,0,0,1)";
    } else {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = this.color;
    }
    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  private endDraw(): void {
    this.drawing = false;
  }

  private coords(e: PointerEvent): { x: number; y: number } {
    const rect = this.canvas!.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * this.canvas!.width,
      y: ((e.clientY - rect.top) / rect.height) * this.canvas!.height,
    };
  }

  /* ── Actions ────────────────────────────────────────────────── */

  private setTool(t: Tool): void {
    this.tool = t;
  }

  private canvasBg(): string {
    const isDark =
      document.documentElement.getAttribute("data-theme") !== "light";
    return isDark ? "#1a1a2e" : "#ffffff";
  }

  private clearCanvas(): void {
    if (!this.ctx || !this.canvas) return;
    this.ctx.globalCompositeOperation = "source-over";
    this.ctx.fillStyle = this.canvasBg();
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
  }

  private done(): void {
    if (!this.canvas) return;
    const dataUrl = this.canvas.toDataURL("image/png");
    this.imageInput.addImageFromDataUrl(dataUrl, "image/png");
    this.close();
  }
}
