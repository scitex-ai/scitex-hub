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
