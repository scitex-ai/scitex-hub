/**
 * BaseResizer — Abstract base for HorizontalResizer and VerticalResizer.
 *
 * Handles state restoration, toggle buttons, collapse/expand.
 * Drag state machine is in drag-handler.ts (attached via attachDragHandler).
 *
 * Subclasses implement axis-specific methods:
 *   getMousePos(e)  — clientX vs clientY
 *   getSize(el)     — offsetWidth vs offsetHeight
 *   setSize(el, px) — width vs flexBasis
 */

import {
  saveSize,
  restoreSize,
  saveCollapsed,
  restoreCollapsed,
} from "./_state";
import { updateToggleIcon, createToggleButton } from "./_toggle";
import { attachDragHandler } from "./_drag-handler";
import type { BaseOpts, PropagationTarget } from "./types";

const LOG = "[Resizer]";

export abstract class BaseResizer {
  protected resizerEl: HTMLElement;
  protected firstPanel: HTMLElement;
  protected secondPanel: HTMLElement;
  protected icon: string;
  protected title: string;
  protected firstCanCollapse: boolean;
  protected secondCanCollapse: boolean;
  protected thresholdPx: number;
  protected isInApp: boolean;
  protected storageKey: string;
  protected accordion: boolean;
  protected snapPointsExplicit: number[];
  private _onDragStart?: () => void;
  private _onDragEnd?: () => void;
  protected externalToggleBtn: HTMLElement | null = null;
  protected toggleBtn: HTMLElement | null = null;

  // Drag state (managed by drag-handler.ts)
  private _isDragging = false;
  private _startPos = 0;
  private _startFirstSize = 0;
  private _startSecondSize = 0;
  private _primaryCollapsed = false;
  private _propagationTarget: PropagationTarget | null = null;

  constructor(
    resizerEl: HTMLElement,
    firstPanel: HTMLElement,
    secondPanel: HTMLElement,
    opts: BaseOpts,
  ) {
    this.resizerEl = resizerEl;
    this.firstPanel = firstPanel;
    this.secondPanel = secondPanel;
    this.icon = opts.icon;
    this.title = opts.title;
    this.firstCanCollapse = opts.firstCanCollapse;
    this.secondCanCollapse = opts.secondCanCollapse;
    this.thresholdPx = opts.thresholdPx;
    this.isInApp = opts.isInApp;
    this.storageKey = opts.storageKey;
    this.accordion = opts.accordion ?? false;
    this.snapPointsExplicit = opts.snapPoints ?? [];
    this._onDragStart = opts.onDragStart;
    this._onDragEnd = opts.onDragEnd;

    if (opts.externalToggleBtnId) {
      this.externalToggleBtn = document.getElementById(
        opts.externalToggleBtnId,
      );
    }

    this.init();
  }

  // --- Abstract axis methods (subclass implements) ---

  protected abstract getMousePos(e: MouseEvent): number;
  protected abstract getSize(el: HTMLElement): number;
  protected abstract setSize(el: HTMLElement, px: number): void;
  protected abstract clearSize(el: HTMLElement): void;
  protected abstract getCursor(): string;

  /** Find cascade target (HorizontalResizer overrides for frame-level) */
  protected findCascadeTarget(
    _panel: HTMLElement,
    _mousePos: number,
  ): PropagationTarget | null {
    return null;
  }

  // --- Public accessors for drag-handler.ts ---

  getResizerEl(): HTMLElement {
    return this.resizerEl;
  }
  getFirstPanel(): HTMLElement {
    return this.firstPanel;
  }
  getSecondPanel(): HTMLElement {
    return this.secondPanel;
  }
  getStorageKey(): string {
    return this.storageKey;
  }
  getThresholdPx(): number {
    return this.thresholdPx;
  }
  getIsInApp(): boolean {
    return this.isInApp;
  }
  getFirstCanCollapse(): boolean {
    return this.firstCanCollapse;
  }
  getSecondCanCollapse(): boolean {
    return this.secondCanCollapse;
  }
  getAccordion(): boolean {
    return this.accordion;
  }
  getSnapPoints(): number[] {
    return this.snapPointsExplicit;
  }
  getCursorPublic(): string {
    return this.getCursor();
  }
  getMousePosPublic(e: MouseEvent): number {
    return this.getMousePos(e);
  }
  getSizePublic(el: HTMLElement): number {
    return this.getSize(el);
  }
  setSizePublic(el: HTMLElement, px: number): void {
    this.setSize(el, px);
  }
  clearSizePublic(el: HTMLElement): void {
    this.clearSize(el);
  }
  getStartPos(): number {
    return this._startPos;
  }
  getStartSizes(): [number, number] {
    return [this._startFirstSize, this._startSecondSize];
  }

  isDraggingNow(): boolean {
    return this._isDragging;
  }
  isPrimaryCollapsed(): boolean {
    return this._primaryCollapsed;
  }
  markPrimaryCollapsed(): void {
    this._primaryCollapsed = true;
  }
  getPropagate(): PropagationTarget | null {
    return this._propagationTarget;
  }
  setPropagate(t: PropagationTarget | null): void {
    this._propagationTarget = t;
  }
  clearPropagate(): void {
    this._propagationTarget = null;
  }
  findCascadeTargetPublic(
    panel: HTMLElement,
    mousePos: number,
  ): PropagationTarget | null {
    return this.findCascadeTarget(panel, mousePos);
  }

  startDrag(e: MouseEvent): void {
    this._isDragging = true;
    this._primaryCollapsed = false;
    this._propagationTarget = null;
    this._startPos = this.getMousePos(e);
    this._startFirstSize = this.getSize(this.firstPanel);
    this._startSecondSize = this.getSize(this.secondPanel);
  }
  endDrag(): void {
    this._isDragging = false;
  }
  fireOnDragStart(): void {
    this._onDragStart?.();
  }
  fireOnDragEnd(): void {
    this._onDragEnd?.();
  }

  isClickOnToggle(e: MouseEvent): boolean {
    return !!(
      this.toggleBtn &&
      (e.target === this.toggleBtn || this.toggleBtn.contains(e.target as Node))
    );
  }

  collapsePanelPublic(which: "first" | "second"): void {
    this.collapsePanel(which);
  }

  saveStatePublic(): void {
    this.saveState();
  }

  // --- Initialization ---

  private init(): void {
    // Prevent double-initialization across Vite bundles.
    // Each bundle has its own module scope, so the module-level Set doesn't help.
    if (this.resizerEl.hasAttribute("data-resizer-initialized")) {
      console.log(`${LOG} Skipping double-init for ${this.storageKey}`);
      return;
    }
    this.resizerEl.setAttribute("data-resizer-initialized", "true");

    // Toggle button: on resizer handle (in-app) or external (frame-level)
    if (this.icon && !this.externalToggleBtn) {
      this.toggleBtn = createToggleButton(
        this.resizerEl,
        this.icon,
        this.title,
      );
      this.toggleBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.handleToggleClick();
      });
    }

    if (this.externalToggleBtn) {
      this.externalToggleBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.handleToggleClick();
      });
    }

    this.restoreState();
    attachDragHandler(this);

    if (this.resizerEl.hasAttribute("data-dblclick-toggle")) {
      this.resizerEl.addEventListener("dblclick", () =>
        this.handleToggleClick(),
      );
    }

    console.log(`${LOG} Initialized ${this.storageKey}`);
  }

  // --- State management ---

  private restoreState(): void {
    this.firstPanel.style.transition = "none";
    this.secondPanel.style.transition = "none";

    const firstCollapsed = restoreCollapsed(this.storageKey + "-first");
    const secondCollapsed = restoreCollapsed(this.storageKey + "-second");

    if (firstCollapsed === true && this.firstCanCollapse) {
      this.collapsePanel("first");
    } else if (secondCollapsed === true && this.secondCanCollapse) {
      this.collapsePanel("second");
    } else {
      // Guard: compute available space so a restored size can't squeeze
      // the opposite panel below threshold (protects against stale values)
      const container = this.firstPanel.parentElement;
      const totalAvailable = container
        ? this.getSize(container)
        : this.getSize(this.firstPanel) + this.getSize(this.secondPanel);

      if (this.firstCanCollapse) {
        const s = restoreSize(this.storageKey + "-first");
        if (
          s &&
          s > this.thresholdPx &&
          s < totalAvailable - this.thresholdPx
        ) {
          this.setSize(this.firstPanel, s);
          this.firstPanel.style.flexShrink = "0";
          this.firstPanel.style.flexGrow = "0";
        }
      }
      if (this.secondCanCollapse) {
        const s = restoreSize(this.storageKey + "-second");
        if (
          s &&
          s > this.thresholdPx &&
          s < totalAvailable - this.thresholdPx
        ) {
          this.setSize(this.secondPanel, s);
          this.secondPanel.style.flexShrink = "0";
          this.secondPanel.style.flexGrow = "0";
        }
      }
    }

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        this.firstPanel.style.transition = "";
        this.secondPanel.style.transition = "";
      });
    });
  }

  protected collapsePanel(which: "first" | "second"): void {
    const panel = which === "first" ? this.firstPanel : this.secondPanel;
    const other = which === "first" ? this.secondPanel : this.firstPanel;

    panel.classList.add("collapsed");
    this.clearSize(panel);
    panel.style.flexShrink = "";
    panel.style.flexGrow = "";

    if (this.accordion) {
      other.classList.add("expanded");
      other.classList.remove("collapsed");
      this.clearSize(other);
      other.style.flexShrink = "";
      other.style.flexGrow = "";
      this.resizerEl.style.display = "none";
    }

    saveCollapsed(this.storageKey + `-${which}`, true);
    this.syncToggleIcon();
  }

  protected expandPanel(which: "first" | "second"): void {
    const panel = which === "first" ? this.firstPanel : this.secondPanel;
    const other = which === "first" ? this.secondPanel : this.firstPanel;

    panel.classList.remove("collapsed");

    if (this.accordion) {
      other.classList.remove("expanded");
      this.resizerEl.style.display = "";
    }

    const saved = restoreSize(this.storageKey + `-${which}`);
    if (saved && saved > this.thresholdPx + 10) {
      this.setSize(panel, saved);
      panel.style.flexShrink = "0";
      panel.style.flexGrow = "0";
    } else {
      this.clearSize(panel);
      panel.style.flexShrink = "";
      panel.style.flexGrow = "";
    }

    saveCollapsed(this.storageKey + `-${which}`, false);
    this.syncToggleIcon();
  }

  private syncToggleIcon(): void {
    const btn = this.toggleBtn || this.externalToggleBtn;
    if (!btn || !this.icon) return;
    const isCollapsed =
      this.firstPanel.classList.contains("collapsed") ||
      this.secondPanel.classList.contains("collapsed");
    updateToggleIcon(btn, this.icon, isCollapsed);
  }

  private handleToggleClick(): void {
    if (this.secondCanCollapse) {
      const c = this.secondPanel.classList.contains("collapsed");
      c ? this.expandPanel("second") : this.collapsePanel("second");
    } else if (this.firstCanCollapse) {
      const c = this.firstPanel.classList.contains("collapsed");
      c ? this.expandPanel("first") : this.collapsePanel("first");
    }
  }

  private saveState(): void {
    if (this.firstCanCollapse) {
      const collapsed = this.firstPanel.classList.contains("collapsed");
      saveCollapsed(this.storageKey + "-first", collapsed);
      if (!collapsed) {
        const s = this.getSize(this.firstPanel);
        if (s > this.thresholdPx) saveSize(this.storageKey + "-first", s);
      }
    }
    if (this.secondCanCollapse) {
      const collapsed = this.secondPanel.classList.contains("collapsed");
      saveCollapsed(this.storageKey + "-second", collapsed);
      if (!collapsed) {
        const s = this.getSize(this.secondPanel);
        if (s > this.thresholdPx) saveSize(this.storageKey + "-second", s);
      }
    }
  }
}
