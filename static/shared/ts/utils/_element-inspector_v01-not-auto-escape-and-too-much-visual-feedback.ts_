/**
 * Element Inspector - Visual Debugging Tool (Refactored)
 *
 * Shows all HTML elements with colored rectangles and labels.
 * Toggle with Alt+I (I for Inspector)
 */

import { OverlayManager } from "./element-inspector/overlay-manager.js";
import { ElementScanner } from "./element-inspector/element-scanner.js";
import { DebugInfoCollector } from "./element-inspector/debug-info-collector.js";
import { SelectionManager } from "./element-inspector/selection-manager.js";
import { NotificationManager } from "./element-inspector/notification-manager.js";
import { PageStructureExporter } from "./element-inspector/page-structure-exporter.js";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/static/shared/ts/utils/element-inspector.ts loaded",
);

class ElementInspector {
  private isActive: boolean = false;
  private overlayManager: OverlayManager;
  private elementScanner: ElementScanner;
  private debugCollector: DebugInfoCollector;
  private selectionManager: SelectionManager;
  private notificationManager: NotificationManager;
  private pageStructureExporter: PageStructureExporter;

  constructor() {
    // Initialize managers with dependency injection
    this.notificationManager = new NotificationManager();
    this.debugCollector = new DebugInfoCollector();
    this.overlayManager = new OverlayManager();

    // Element scanner needs debug collector and notification manager
    this.elementScanner = new ElementScanner(
      this.debugCollector,
      this.notificationManager,
    );

    // Selection manager needs element box map, debug collector, and notification manager
    this.selectionManager = new SelectionManager(
      this.elementScanner.getElementBoxMap(),
      this.debugCollector,
      this.notificationManager,
    );

    // Page structure exporter needs notification manager
    this.pageStructureExporter = new PageStructureExporter(
      this.notificationManager,
    );

    this.init();
  }

  private init(): void {
    // Add keyboard shortcuts
    document.addEventListener("keydown", (e: KeyboardEvent) => {
      // Alt+I: Toggle inspector
      if (e.altKey && !e.shiftKey && !e.ctrlKey && e.key === "i") {
        e.preventDefault();
        this.toggle();
      }

      // Alt+C: Copy full page structure
      if (
        e.altKey &&
        !e.shiftKey &&
        !e.ctrlKey &&
        (e.key === "c" || e.key === "C")
      ) {
        e.preventDefault();
        this.pageStructureExporter.copyPageStructure();
      }

      // Ctrl+Alt+I: Start rectangle selection mode
      if (e.ctrlKey && e.altKey && !e.shiftKey && e.key === "i") {
        e.preventDefault();
        this.startSelectionMode();
      }

      // Escape: Deactivate inspector and cancel selection mode
      if (e.key === "Escape") {
        e.preventDefault();
        if (this.selectionManager.isActive()) {
          this.selectionManager.cancelSelectionMode();
          this.deactivate();
        } else if (this.isActive) {
          this.deactivate();
        }
      }
    });

    console.log("[ElementInspector] Initialized");
    console.log("  Alt+I: Toggle inspector overlay");
    console.log("  Alt+C: Copy full page structure");
    console.log("  Ctrl+Alt+I: Rectangle selection mode");
    console.log("  Escape: Deactivate inspector / Cancel selection");
  }

  public toggle(): void {
    if (this.isActive) {
      this.deactivate();
    } else {
      this.activate();
    }
  }

  private activate(): void {
    console.log("[ElementInspector] Activating...");
    this.isActive = true;

    // Create overlay container
    const overlayContainer = this.overlayManager.createOverlay();

    // Scan all elements and create overlays
    this.elementScanner.scanElements(overlayContainer);

    console.log("[ElementInspector] Active - Press Alt+I to deactivate");
  }

  private deactivate(): void {
    console.log("[ElementInspector] Deactivating...");
    this.isActive = false;

    // Clear element map
    this.elementScanner.clearElementBoxMap();

    // Remove overlay
    this.overlayManager.removeOverlay();
  }

  public refresh(): void {
    if (this.isActive) {
      this.deactivate();
      this.activate();
    }
  }

  private startSelectionMode(): void {
    // Activate element visualization if not already active
    if (!this.isActive) {
      this.activate();
    }

    // Start selection mode
    this.selectionManager.startSelectionMode();
  }
}

// Initialize global instance
const elementInspector = new ElementInspector();

// Export to window for manual control
(window as any).elementInspector = elementInspector;

// Auto-refresh on window resize (with debounce)
let resizeTimeout: number;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = window.setTimeout(() => {
    if ((window as any).elementInspector?.isActive) {
      (window as any).elementInspector.refresh();
    }
  }, 500);
});
