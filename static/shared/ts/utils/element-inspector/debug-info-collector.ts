/**
 * Debug Info Collector for Element Inspector
 * Gathers comprehensive debugging information about elements
 */

import type { ElementDebugInfo, CSSRuleInfo } from "./types.js";

export class DebugInfoCollector {
  public gatherElementDebugInfo(element: Element): string {
    const info: any = {};

    // Page Context
    info.url = window.location.href;
    info.timestamp = new Date().toISOString();

    // Element Identification
    const className =
      typeof element.className === "string" ? element.className : "";
    info.element = {
      tag: element.tagName.toLowerCase(),
      id: element.id || null,
      classes: className ? className.split(/\s+/).filter((c) => c) : [],
      selector: this.buildCSSSelector(element),
      xpath: this.getXPath(element),
    };

    // Attributes
    info.attributes = {};
    for (let i = 0; i < element.attributes.length; i++) {
      const attr = element.attributes[i];
      info.attributes[attr.name] = attr.value;
    }

    // Get computed styles (important ones)
    if (element instanceof HTMLElement) {
      const computed = window.getComputedStyle(element);
      info.styles = {
        display: computed.display,
        position: computed.position,
        width: computed.width,
        height: computed.height,
        margin: computed.margin,
        padding: computed.padding,
        backgroundColor: computed.backgroundColor,
        color: computed.color,
        fontSize: computed.fontSize,
        fontFamily: computed.fontFamily,
        zIndex: computed.zIndex,
        opacity: computed.opacity,
        visibility: computed.visibility,
        overflow: computed.overflow,
      };

      // Inline styles
      if (element.style.cssText) {
        info.inlineStyles = element.style.cssText;
      }

      // Dimensions and position
      const rect = element.getBoundingClientRect();
      info.dimensions = {
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
        bottom: rect.bottom,
        right: rect.right,
      };

      // Scroll position
      info.scroll = {
        scrollTop: element.scrollTop,
        scrollLeft: element.scrollLeft,
        scrollHeight: element.scrollHeight,
        scrollWidth: element.scrollWidth,
      };

      // Inner content (truncated)
      info.content = {
        innerHTML:
          element.innerHTML.substring(0, 200) +
          (element.innerHTML.length > 200 ? "..." : ""),
        textContent:
          element.textContent?.substring(0, 200) +
          (element.textContent && element.textContent.length > 200
            ? "..."
            : ""),
      };
    }

    // Event listeners (simplified - can't get all listeners easily)
    info.eventListeners = this.getEventListeners(element);

    // Parent chain
    info.parentChain = this.getParentChain(element);

    // Applied CSS files (approximation via stylesheets)
    info.appliedStylesheets = this.getAppliedStylesheets();

    // Try to find CSS rules that match this element
    info.matchingCSSRules = this.getMatchingCSSRules(element);

    // Format as readable text for AI
    return this.formatDebugInfoForAI(info);
  }

  public buildCSSSelector(element: Element): string {
    const tag = element.tagName.toLowerCase();
    const id = element.id;
    const classes = element.className;

    let selector = tag;
    if (id) {
      selector += `#${id}`;
    }
    if (classes && typeof classes === "string") {
      const classList = classes.split(/\s+/).filter((c) => c);
      if (classList.length > 0) {
        selector += `.${classList.join(".")}`;
      }
    }
    return selector;
  }

  public getXPath(element: Element): string {
    if (element.id) {
      return `//*[@id="${element.id}"]`;
    }

    const parts: string[] = [];
    let current: Element | null = element;

    while (current && current.nodeType === Node.ELEMENT_NODE) {
      let index = 0;
      let sibling = current.previousSibling;

      while (sibling) {
        if (
          sibling.nodeType === Node.ELEMENT_NODE &&
          sibling.nodeName === current.nodeName
        ) {
          index++;
        }
        sibling = sibling.previousSibling;
      }

      const tagName = current.nodeName.toLowerCase();
      const pathIndex = index > 0 ? `[${index + 1}]` : "";
      parts.unshift(tagName + pathIndex);

      current = current.parentElement;
    }

    return "/" + parts.join("/");
  }

  private getEventListeners(element: Element): string[] {
    // Note: Can't easily get all event listeners without Chrome DevTools API
    // But we can check common event attributes
    const listeners: string[] = [];
    const eventAttrs = [
      "onclick",
      "onload",
      "onchange",
      "onsubmit",
      "onmouseover",
      "onmouseout",
    ];

    eventAttrs.forEach((attr) => {
      if (element.hasAttribute(attr)) {
        listeners.push(attr);
      }
    });

    return listeners;
  }

  private getParentChain(element: Element): string[] {
    const chain: string[] = [];
    let current = element.parentElement;
    let depth = 0;

    while (current && depth < 5) {
      chain.push(this.buildCSSSelector(current));
      current = current.parentElement;
      depth++;
    }

    return chain;
  }

  private getAppliedStylesheets(): string[] {
    const sheets: string[] = [];

    for (let i = 0; i < document.styleSheets.length; i++) {
      try {
        const sheet = document.styleSheets[i];
        if (sheet.href) {
          sheets.push(sheet.href);
        } else if (sheet.ownerNode) {
          sheets.push("<inline style>");
        }
      } catch (e) {
        // CORS restrictions might prevent access
        sheets.push("<cross-origin stylesheet>");
      }
    }

    return sheets;
  }

  private getMatchingCSSRules(element: Element): CSSRuleInfo[] {
    const matchingRules: CSSRuleInfo[] = [];

    for (let i = 0; i < document.styleSheets.length; i++) {
      try {
        const sheet = document.styleSheets[i];
        if (!sheet.cssRules) continue;

        for (let j = 0; j < sheet.cssRules.length; j++) {
          const rule = sheet.cssRules[j];

          if (rule instanceof CSSStyleRule) {
            // Check if this rule's selector matches our element
            try {
              if (element.matches(rule.selectorText)) {
                matchingRules.push({
                  selector: rule.selectorText,
                  cssText:
                    rule.cssText.substring(0, 200) +
                    (rule.cssText.length > 200 ? "..." : ""),
                  source: sheet.href || "<inline style>",
                  ruleIndex: j,
                });
              }
            } catch (e) {
              // Invalid selector or other error
            }
          }
        }
      } catch (e) {
        // CORS or other restrictions
      }
    }

    return matchingRules;
  }

  private formatDebugInfoForAI(info: ElementDebugInfo): string {
    return `# Element Debug Information

## Page Context
- URL: ${info.url}
- Timestamp: ${info.timestamp}

## Element Identification
- Tag: <${info.element.tag}>
- ID: ${info.element.id || "none"}
- Classes: ${info.element.classes.join(", ") || "none"}
- CSS Selector: ${info.element.selector}
- XPath: ${info.element.xpath}

## Attributes
${Object.entries(info.attributes)
  .map(([key, value]) => `- ${key}: ${value}`)
  .join("\n")}

## Computed Styles
${Object.entries(info.styles || {})
  .map(([key, value]) => `- ${key}: ${value}`)
  .join("\n")}

${info.inlineStyles ? `## Inline Styles\n${info.inlineStyles}\n` : ""}

## Dimensions & Position
- Width: ${info.dimensions?.width}px
- Height: ${info.dimensions?.height}px
- Top: ${info.dimensions?.top}px
- Left: ${info.dimensions?.left}px

## Scroll State
- scrollTop: ${info.scroll?.scrollTop}
- scrollLeft: ${info.scroll?.scrollLeft}

## Content (truncated)
${info.content?.textContent || "none"}

## Event Listeners
${info.eventListeners.length > 0 ? info.eventListeners.join(", ") : "none detected"}

## Parent Chain
${info.parentChain.map((p: string, i: number) => `${i + 1}. ${p}`).join("\n")}

## Applied Stylesheets
${info.appliedStylesheets
  .slice(0, 10)
  .map((s: string, i: number) => `${i + 1}. ${s}`)
  .join("\n")}

## Matching CSS Rules (${info.matchingCSSRules?.length || 0} rules)
${
  info.matchingCSSRules && info.matchingCSSRules.length > 0
    ? info.matchingCSSRules
        .slice(0, 10)
        .map(
          (rule: CSSRuleInfo, i: number) => `
### ${i + 1}. ${rule.selector}
- Source: ${rule.source}
- Rule Index: ${rule.ruleIndex}
- CSS: ${rule.cssText}
`,
        )
        .join("\n")
    : "No matching rules found (may be due to CORS restrictions)"
}

---
This debug information was captured by Element Inspector and can be used for AI-assisted debugging.
Note: Exact CSS line numbers require browser DevTools API access.
`;
  }
}
