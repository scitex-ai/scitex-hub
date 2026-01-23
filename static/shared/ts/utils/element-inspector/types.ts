/**
 * Type definitions for Element Inspector
 */

export interface ElementDebugInfo {
  url: string;
  timestamp: string;
  element: {
    tag: string;
    id: string | null;
    classes: string[];
    selector: string;
    xpath: string;
  };
  attributes: Record<string, string>;
  styles?: Record<string, string>;
  inlineStyles?: string;
  dimensions?: {
    width: number;
    height: number;
    top: number;
    left: number;
    bottom: number;
    right: number;
  };
  scroll?: {
    scrollTop: number;
    scrollLeft: number;
    scrollHeight: number;
    scrollWidth: number;
  };
  content?: {
    innerHTML: string;
    textContent: string;
  };
  eventListeners: string[];
  parentChain: string[];
  appliedStylesheets: string[];
  matchingCSSRules: CSSRuleInfo[];
}

export interface CSSRuleInfo {
  selector: string;
  cssText: string;
  source: string;
  ruleIndex: number;
}

export interface LabelPosition {
  top: number;
  left: number;
  isValid: boolean;
}

export interface OccupiedPosition {
  top: number;
  left: number;
  bottom: number;
  right: number;
}

export interface SelectionRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface PageStructureInfo {
  url: string;
  timestamp: string;
  viewport: {
    width: number;
    height: number;
    scrollX: number;
    scrollY: number;
  };
  document: {
    title: string;
    doctype: string;
    characterSet: string;
    readyState: string;
  };
  structure: any;
  stylesheets: any[];
  scripts: any[];
}
