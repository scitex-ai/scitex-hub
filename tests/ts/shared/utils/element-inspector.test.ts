/**
 * Tests for static/shared/ts/utils/element-inspector.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/static/shared/ts/utils/element-inspector';

describe('element-inspector', () => {
    const FLAG = '__scitexElementInspectorLoaded';

    beforeEach(() => {
        document.body.innerHTML = '';
    });

    afterEach(() => {
        document.body.innerHTML = '';
        delete (window as any)[FLAG];
        delete (window as any).elementInspector;
        vi.resetModules();
        vi.restoreAllMocks();
    });

    async function importFresh() {
        vi.resetModules();
        return await import(
            '../../../../static/shared/ts/utils/element-inspector'
        );
    }

    function pressAltI(target: EventTarget = document): KeyboardEvent {
        const event = new KeyboardEvent('keydown', {
            key: 'i',
            altKey: true,
            bubbles: true,
            cancelable: true,
        });
        target.dispatchEvent(event);
        return event;
    }

    it('a second evaluation in the same document constructs no second inspector', async () => {
        // Arrange — the double-script-include of card
        // hub-element-inspector-double-invocation-20261019: the same module
        // evaluated twice in one document.
        await importFresh();
        await importFresh();

        // Act — one Alt+I keydown.
        pressAltI();

        // Assert — exactly one overlay, not one per evaluation.
        expect(
            document.querySelectorAll('#element-inspector-overlay').length,
        ).toBe(1);
    });

    it('defers to an already-present foreign inspector copy', async () => {
        // Arrange — e.g. the SDK/middleware bundle loaded first.
        const foreign = { isActive: false };
        (window as any).elementInspector = foreign;

        // Act
        await importFresh();

        // Assert — this copy must not construct over it.
        expect((window as any).elementInspector).toBe(foreign);
        expect((window as any)[FLAG]).toBeUndefined();
    });

    it('stopPropagation keeps a single Alt+I from reaching the window', async () => {
        // Arrange
        await importFresh();
        const probe = vi.fn();
        window.addEventListener('keydown', probe);

        // Act
        pressAltI();

        // Assert — the toggle consumed the event at the document.
        expect(probe).not.toHaveBeenCalled();
        window.removeEventListener('keydown', probe);
    });
});

// ==============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// ==============================================================================
// Source: static/shared/ts/utils/element-inspector.ts
// ==============================================================================

// /**
//  * Element Inspector - Visual Debugging Tool (Refactored)
//  *
//  * Shows all HTML elements with colored rectangles and labels.
//  * Toggle with Alt+I (I for Inspector)
//  */
// 
// import { OverlayManager } from "./_element-inspector/_overlay-manager";
// import { ElementScanner } from "./_element-inspector/_element-scanner";
// import { DebugInfoCollector } from "./_element-inspector/_debug-info-collector";
// import { SelectionManager } from "./_element-inspector/_selection-manager";
// import { NotificationManager } from "./_element-inspector/_notification-manager";
// import { PageStructureExporter } from "./_element-inspector/_page-structure-exporter";
// import { ConsoleCollector } from "./_element-inspector/_console-collector";
// 
// class ElementInspector {
//   private isActive: boolean = false;
//   private overlayManager: OverlayManager;
//   private elementScanner: ElementScanner;
//   private debugCollector: DebugInfoCollector;
//   private selectionManager: SelectionManager;
//   private notificationManager: NotificationManager;
//   private pageStructureExporter: PageStructureExporter;
//   private consoleCollector: ConsoleCollector;
// 
//   constructor() {
//     // Initialize managers with dependency injection
//     this.notificationManager = new NotificationManager();
//     this.debugCollector = new DebugInfoCollector();
//     this.overlayManager = new OverlayManager();
// 
//     // Element scanner needs debug collector and notification manager
//     this.elementScanner = new ElementScanner(
//       this.debugCollector,
//       this.notificationManager,
//     );
// 
//     // Selection manager needs element box map, debug collector, and notification manager
//     this.selectionManager = new SelectionManager(
//       this.elementScanner.getElementBoxMap(),
//       this.debugCollector,
//       this.notificationManager,
//     );
// 
//     // Set element scanner reference for depth-aware selection
//     this.selectionManager.setElementScanner(this.elementScanner);
// 
//     // Page structure exporter needs notification manager
//     this.pageStructureExporter = new PageStructureExporter(
//       this.notificationManager,
//     );
// 
//     // Console collector for debug snapshots
//     this.consoleCollector = new ConsoleCollector(this.notificationManager);
// 
//     // Set up auto-dismiss callback - deactivate after successful copy
//     this.notificationManager.setOnCopyCallback(() => {
//       this.deactivate();
//     });
// 
//     this.init();
//   }
// 
//   private init(): void {
//     // Add keyboard shortcuts
//     document.addEventListener("keydown", (e: KeyboardEvent) => {
//       const key = e.key.toLowerCase();
// 
//       // FIRST: Always allow Tab, Enter, Arrow keys to pass through normally
//       // These should never be intercepted by the element inspector
//       if (["Tab", "Enter", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) {
//         return; // Don't handle these keys at all
//       }
// 
//       // Ctrl+Shift+I: Capture debug snapshot (screenshot + console logs)
//       // Check this FIRST before other "i" handlers
//       if (e.ctrlKey && e.shiftKey && !e.altKey && key === "i") {
//         e.preventDefault();
//         e.stopPropagation();
//         console.log("[ElementInspector] Ctrl+Shift+I pressed - capturing debug snapshot");
//         this.consoleCollector.captureDebugSnapshot();
//         return;
//       }
// 
//       // Ctrl+Alt+I: Start rectangle selection mode
//       if (e.ctrlKey && e.altKey && !e.shiftKey && key === "i") {
//         e.preventDefault();
//         e.stopPropagation();
//         this.startSelectionMode();
//         return;
//       }
// 
//       // Ctrl+I: Load next batch of elements (when inspector is active)
//       if (e.ctrlKey && !e.altKey && !e.shiftKey && key === "i") {
//         if (this.isActive) {
//           e.preventDefault();
//           e.stopPropagation();
//           console.log("[ElementInspector] Ctrl+I pressed - loading next batch");
//           this.elementScanner.loadNextBatch();
//           return;
//         }
//       }
// 
//       // Alt+I: Toggle inspector (no Ctrl, no Shift)
//       if (e.altKey && !e.shiftKey && !e.ctrlKey && key === "i") {
//         e.preventDefault();
//         e.stopPropagation();
//         this.toggle();
//         return;
//       }
// 
//       // Escape: Deactivate inspector and cancel selection mode
//       if (e.key === "Escape") {
//         if (this.selectionManager.isActive()) {
//           e.preventDefault();
//           this.selectionManager.cancelSelectionMode();
//           this.deactivate();
//         } else if (this.isActive) {
//           e.preventDefault();
//           this.deactivate();
//         }
//         // If not active, let Escape pass through
//         return;
//       }
//     });
// 
//     console.log("[ElementInspector] Initialized");
//     console.log("  Alt+I: Toggle inspector overlay");
//     console.log("  Ctrl+I: Load next 512 elements (when active)");
//     console.log("  Ctrl+Alt+I: Rectangle selection mode");
//     console.log("  Ctrl+Shift+I: Debug snapshot (screenshot + console logs)");
//     console.log("  Scroll wheel: Cycle through overlapped elements (affects rect selection depth)");
//     console.log("  Right-click: Copy element debug info");
//     console.log("  Left-click: Pass through to underlying element");
//     console.log("  Escape: Deactivate inspector / Cancel selection");
//   }
// 
//   public toggle(): void {
//     if (this.isActive) {
//       this.deactivate();
//     } else {
//       this.activate();
//     }
//   }
// 
//   private activate(): void {
//     console.log("[ElementInspector] Activating...");
//     this.isActive = true;
// 
//     // Create overlay container
//     const overlayContainer = this.overlayManager.createOverlay();
// 
//     // Scan all elements and create overlays
//     this.elementScanner.scanElements(overlayContainer);
// 
//     console.log("[ElementInspector] Active - Press Alt+I to deactivate");
//   }
// 
//   private deactivate(): void {
//     console.log("[ElementInspector] Deactivating...");
//     this.isActive = false;
// 
//     // Clear element map
//     this.elementScanner.clearElementBoxMap();
// 
//     // Remove overlay
//     this.overlayManager.removeOverlay();
//   }
// 
//   public refresh(): void {
//     if (this.isActive) {
//       this.deactivate();
//       this.activate();
//     }
//   }
// 
//   private startSelectionMode(): void {
//     // Activate element visualization if not already active
//     if (!this.isActive) {
//       this.activate();
//     }
// 
//     // Start selection mode
//     this.selectionManager.startSelectionMode();
//   }
// }
// 
// // Initialize the global instance exactly once per document. A second
// // evaluation of this module in the same document (double script include)
// // — or a foreign copy of the inspector bundle loading alongside this one —
// // must not construct a second inspector: each instance registers its own
// // document keydown listener, so two instances double-invoke Alt+I and
// // create duplicate #element-inspector-overlay elements (card
// // hub-element-inspector-double-invocation-20261019). The per-evaluation
// // `instanceof` check alone cannot catch a foreign copy (distinct class
// // identity), hence the shared window-level loaded flag.
// const INSPECTOR_LOADED_FLAG = "__scitexElementInspectorLoaded";
// 
// if (
//   !(window as any)[INSPECTOR_LOADED_FLAG] &&
//   !(window as any).elementInspector
// ) {
//   const elementInspector = new ElementInspector();
// 
//   // Export to window for manual control
//   (window as any).elementInspector = elementInspector;
//   (window as any)[INSPECTOR_LOADED_FLAG] = true;
// }
// 
// // Auto-refresh on window resize (with debounce)
// let resizeTimeout: number;
// window.addEventListener("resize", () => {
//   clearTimeout(resizeTimeout);
//   resizeTimeout = window.setTimeout(() => {
//     if ((window as any).elementInspector?.isActive) {
//       (window as any).elementInspector.refresh();
//     }
//   }, 500);
// });

// ==============================================================================
// End of Source Code
// ==============================================================================
