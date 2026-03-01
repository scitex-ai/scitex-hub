/**
 * Vertical Split Resizer
 * Drag-to-resize divider between file tree and repo monitor panels
 */

const STORAGE_KEY = "scitex-repo-monitor-split-ratio";
const COLLAPSE_THRESHOLD_PX = 40;
const DEFAULT_TOP_RATIO = 0.6;

export class VerticalSplitResizer {
  private resizer: HTMLElement;
  private topPanel: HTMLElement;
  private bottomPanel: HTMLElement;

  private isDragging = false;
  private startY = 0;
  private startTopHeight = 0;
  private totalHeight = 0;

  private boundMouseMove: (e: MouseEvent) => void;
  private boundMouseUp: (e: MouseEvent) => void;
  private rafId: number | null = null;
  private pendingY: number | null = null;

  constructor(
    resizer: HTMLElement,
    topPanel: HTMLElement,
    bottomPanel: HTMLElement,
  ) {
    this.resizer = resizer;
    this.topPanel = topPanel;
    this.bottomPanel = bottomPanel;

    this.boundMouseMove = this.onMouseMove.bind(this);
    this.boundMouseUp = this.onMouseUp.bind(this);

    this.resizer.addEventListener("mousedown", this.onMouseDown.bind(this));
    this.resizer.addEventListener("dblclick", this.onDoubleClick.bind(this));
  }

  private onMouseDown(e: MouseEvent): void {
    e.preventDefault();
    this.isDragging = true;
    this.startY = e.clientY;
    this.startTopHeight = this.topPanel.getBoundingClientRect().height;
    this.totalHeight =
      this.topPanel.getBoundingClientRect().height +
      this.bottomPanel.getBoundingClientRect().height;

    this.resizer.classList.add("active");
    document.addEventListener("mousemove", this.boundMouseMove);
    document.addEventListener("mouseup", this.boundMouseUp);
  }

  private onMouseMove(e: MouseEvent): void {
    if (!this.isDragging) return;
    this.pendingY = e.clientY;

    if (this.rafId === null) {
      this.rafId = requestAnimationFrame(() => {
        this.rafId = null;
        if (this.pendingY !== null) {
          this.applyResize(this.pendingY);
          this.pendingY = null;
        }
      });
    }
  }

  private applyResize(clientY: number): void {
    const delta = clientY - this.startY;
    const newTopHeight = Math.max(
      COLLAPSE_THRESHOLD_PX,
      this.startTopHeight + delta,
    );
    const newBottomHeight = Math.max(0, this.totalHeight - newTopHeight);

    this.topPanel.style.flexBasis = `${newTopHeight}px`;
    this.bottomPanel.style.flexBasis = `${newBottomHeight}px`;

    if (newBottomHeight < COLLAPSE_THRESHOLD_PX) {
      this.bottomPanel.classList.add("collapsed");
    } else {
      this.bottomPanel.classList.remove("collapsed");
    }
  }

  private onMouseUp(e: MouseEvent): void {
    if (!this.isDragging) return;
    this.isDragging = false;
    this.resizer.classList.remove("active");

    document.removeEventListener("mousemove", this.boundMouseMove);
    document.removeEventListener("mouseup", this.boundMouseUp);

    this.saveRatio();
  }

  private onDoubleClick(): void {
    const bottomCollapsed = this.bottomPanel.classList.contains("collapsed");
    const containerHeight =
      this.topPanel.getBoundingClientRect().height +
      this.bottomPanel.getBoundingClientRect().height;

    if (bottomCollapsed) {
      // Restore 50/50
      const half = containerHeight / 2;
      this.topPanel.style.flexBasis = `${half}px`;
      this.bottomPanel.style.flexBasis = `${half}px`;
      this.bottomPanel.classList.remove("collapsed");
    } else {
      // Collapse bottom
      this.topPanel.style.flexBasis = `${containerHeight}px`;
      this.bottomPanel.style.flexBasis = "0px";
      this.bottomPanel.classList.add("collapsed");
    }

    this.saveRatio();
  }

  restoreState(): void {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) {
        this.applyRatio(DEFAULT_TOP_RATIO);
        return;
      }
      const ratio = parseFloat(saved);
      if (!isNaN(ratio) && ratio >= 0 && ratio <= 1) {
        this.applyRatio(ratio);
      }
    } catch {
      this.applyRatio(DEFAULT_TOP_RATIO);
    }
  }

  private applyRatio(topRatio: number): void {
    const container = this.topPanel.parentElement ?? document.documentElement;
    const totalHeight = container.getBoundingClientRect().height;

    if (totalHeight === 0) return;

    const topHeight = totalHeight * topRatio;
    const bottomHeight = totalHeight * (1 - topRatio);

    this.topPanel.style.flexBasis = `${topHeight}px`;
    this.bottomPanel.style.flexBasis = `${bottomHeight}px`;

    if (bottomHeight < COLLAPSE_THRESHOLD_PX) {
      this.bottomPanel.classList.add("collapsed");
    } else {
      this.bottomPanel.classList.remove("collapsed");
    }
  }

  private saveRatio(): void {
    const topHeight = this.topPanel.getBoundingClientRect().height;
    const bottomHeight = this.bottomPanel.getBoundingClientRect().height;
    const total = topHeight + bottomHeight;
    if (total === 0) return;

    const ratio = topHeight / total;
    try {
      localStorage.setItem(STORAGE_KEY, ratio.toFixed(4));
    } catch {
      // ignore
    }
  }
}
