/**
 * Element Inspector - Visual Debugging Tool (Refactored)
 *
 * Shows all HTML elements with colored rectangles and labels.
 * Toggle with Alt+I (I for Inspector)
 */

import { OverlayManager } from "./_element-inspector/_overlay-manager";
import { ElementScanner } from "./_element-inspector/_element-scanner";
import { DebugInfoCollector } from "./_element-inspector/_debug-info-collector";
import { SelectionManager } from "./_element-inspector/_selection-manager";
import { NotificationManager } from "./_element-inspector/_notification-manager";
import { PageStructureExporter } from "./_element-inspector/_page-structure-exporter";
import { ConsoleCollector } from "./_element-inspector/_console-collector";

class ElementInspector {
  private isActive: boolean = false;
  private overlayManager: OverlayManager;
  private elementScanner: ElementScanner;
  private debugCollector: DebugInfoCollector;
  private selectionManager: SelectionManager;
  private notificationManager: NotificationManager;
  private pageStructureExporter: PageStructureExporter;
  private consoleCollector: ConsoleCollector;

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

    // Set element scanner reference for depth-aware selection
    this.selectionManager.setElementScanner(this.elementScanner);

    // Page structure exporter needs notification manager
    this.pageStructureExporter = new PageStructureExporter(
      this.notificationManager,
    );

    // Console collector for debug snapshots
    this.consoleCollector = new ConsoleCollector(this.notificationManager);

    // Set up auto-dismiss callback - deactivate after successful copy
    this.notificationManager.setOnCopyCallback(() => {
      this.deactivate();
    });

    this.init();
  }

  private init(): void {
    // Add keyboard shortcuts
    document.addEventListener("keydown", (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();

      // FIRST: Always allow Tab, Enter, Arrow keys to pass through normally
      // These should never be intercepted by the element inspector
      if (["Tab", "Enter", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) {
        return; // Don't handle these keys at all
      }

      // Ctrl+Shift+I: Capture debug snapshot (screenshot + console logs)
      // Check this FIRST before other "i" handlers
      if (e.ctrlKey && e.shiftKey && !e.altKey && key === "i") {
        e.preventDefault();
        e.stopPropagation();
        console.log("[ElementInspector] Ctrl+Shift+I pressed - capturing debug snapshot");
        this.consoleCollector.captureDebugSnapshot();
        return;
      }

      // Ctrl+Alt+I: Start rectangle selection mode
      if (e.ctrlKey && e.altKey && !e.shiftKey && key === "i") {
        e.preventDefault();
        this.startSelectionMode();
        return;
      }

      // Ctrl+I: Load next batch of elements (when inspector is active)
      if (e.ctrlKey && !e.altKey && !e.shiftKey && key === "i") {
        if (this.isActive) {
          e.preventDefault();
          console.log("[ElementInspector] Ctrl+I pressed - loading next batch");
          this.elementScanner.loadNextBatch();
          return;
        }
      }

      // Alt+I: Toggle inspector (no Ctrl, no Shift)
      if (e.altKey && !e.shiftKey && !e.ctrlKey && key === "i") {
        e.preventDefault();
        this.toggle();
        return;
      }

      // Escape: Deactivate inspector and cancel selection mode
      if (e.key === "Escape") {
        if (this.selectionManager.isActive()) {
          e.preventDefault();
          this.selectionManager.cancelSelectionMode();
          this.deactivate();
        } else if (this.isActive) {
          e.preventDefault();
          this.deactivate();
        }
        // If not active, let Escape pass through
        return;
      }
    });

    console.log("[ElementInspector] Initialized");
    console.log("  Alt+I: Toggle inspector overlay");
    console.log("  Ctrl+I: Load next 512 elements (when active)");
    console.log("  Ctrl+Alt+I: Rectangle selection mode");
    console.log("  Ctrl+Shift+I: Debug snapshot (screenshot + console logs)");
    console.log("  Scroll wheel: Cycle through overlapped elements (affects rect selection depth)");
    console.log("  Right-click: Copy element debug info");
    console.log("  Left-click: Pass through to underlying element");
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
