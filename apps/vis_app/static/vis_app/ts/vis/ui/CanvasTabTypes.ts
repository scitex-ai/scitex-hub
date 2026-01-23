/**
 * Type definitions for canvas tab management
 */

export interface CanvasTab {
  id: string;
  figureName: string;
  isActive: boolean;
  /** File path of the figz bundle (for tree sync) */
  figurePath?: string;
  /** IDs of linked data tables - bidirectional link with DataTab.linkedFigureId */
  linkedDataTableIds?: string[];
  /** Serialized canvas JSON (fabric.js toJSON output) */
  canvasJson?: any;
  /** View state: zoom level and pan offset */
  viewState?: {
    zoom: number;
    panX: number;
    panY: number;
  };
}

export interface TabCallbacks {
  onBeforeTabChange: (() => void) | null;
  onTabChange: ((tabId: string) => void) | null;
  onTabClose: ((tabId: string) => void) | null;
  onTabRename: ((tabId: string, newName: string) => void) | null;
  onBundleCreated: ((figureName: string, figurePath: string) => void) | null;
}

export interface TabViewState {
  zoom: number;
  panX: number;
  panY: number;
}
