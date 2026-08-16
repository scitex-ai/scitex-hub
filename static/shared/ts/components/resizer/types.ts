/**
 * Type definitions for the unified Resizer system.
 *
 * Two resizer types sharing a common base:
 *   HorizontalResizer — left/right panels, X-axis drag
 *   VerticalResizer   — top/bottom panels, Y-axis drag
 */

/** Configuration for HorizontalResizer */
export interface HorizontalConfig {
  left: string;
  right: string;
  icon: string;
  title: string;
  isMostLeft: boolean;
  isMostRight: boolean;
  thresholdPx: number;
  isInApp: boolean;
  storageKey?: string;
  onDragStart?: () => void;
  onDragEnd?: () => void;
  externalToggleBtnId?: string;
  accordion?: boolean;
  snapPoints?: number[];
  /**
   * On a phone-width viewport, collapse the SECOND (right) panel rather than
   * the first. Set via `data-collapse-on-narrow` on the resizer element.
   *
   * OFF BY DEFAULT AND OPT-IN PER RESIZER. The narrow-viewport rule in
   * BaseResizer.restoreState() was written for a left sidebar and collapses
   * the FIRST panel, which is correct for most consumers and catastrophic for
   * Writer: its resizer declares data-left=".writer-container" (the document),
   * so a phone collapsed the editor and left the Details panel spanning the
   * whole workspace. Opt-in keeps every other consumer byte-for-byte unchanged
   * — notably Scholar's library panes, whose mobile layout already works as
   * scroll-snap swipe pages and must not be collapsed.
   */
  collapseOnNarrow?: boolean;
}

/** Configuration for VerticalResizer */
export interface VerticalConfig {
  top: string;
  bottom: string;
  icon: string;
  title: string;
  isMostTop: boolean;
  isMostBottom: boolean;
  thresholdPx: number;
  isInApp: boolean;
  storageKey?: string;
  onDragStart?: () => void;
  onDragEnd?: () => void;
  accordion?: boolean;
  snapPoints?: number[];
}

/** Internal options passed from subclass to BaseResizer */
export interface BaseOpts {
  icon: string;
  title: string;
  firstCanCollapse: boolean;
  secondCanCollapse: boolean;
  thresholdPx: number;
  isInApp: boolean;
  storageKey: string;
  onDragStart?: () => void;
  onDragEnd?: () => void;
  externalToggleBtnId?: string;
  accordion?: boolean;
  snapPoints?: number[];
  /** See HorizontalConfig.collapseOnNarrow — opt-in, off by default. */
  collapseOnNarrow?: boolean;
}

/** Cascade propagation target tracked during a drag operation */
export interface PropagationTarget {
  panel: HTMLElement;
  storageKey: string;
  startSize: number;
  startPos: number;
  thresholdPx: number;
  toggleBtn: HTMLElement | null;
  toggleIcon: string;
}
