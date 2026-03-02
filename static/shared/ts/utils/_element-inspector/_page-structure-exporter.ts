/**
 * Page Structure Exporter for Element Inspector
 * Exports complete page structure for AI analysis
 */

import type { PageStructureInfo } from "./types";
import { NotificationManager } from "./_notification-manager";

export class PageStructureExporter {
  private notificationManager: NotificationManager;

  constructor(notificationManager: NotificationManager) {
    this.notificationManager = notificationManager;
  }

  public async copyPageStructure(): Promise<void> {
    console.log("[ElementInspector] Generating full page structure...");

    this.notificationManager.showCameraFlash();

    const structure = this.generatePageStructure();

    try {
      await navigator.clipboard.writeText(structure);
      console.log("[ElementInspector] Page structure copied to clipboard!");

      this.notificationManager.showNotification(
        "✓ Page structure copied!",
        "success",
      );

      // Trigger auto-dismiss (ESC) after copy
      this.notificationManager.triggerCopyCallback();
    } catch (err) {
      console.error("[ElementInspector] Failed to copy page structure:", err);
      this.notificationManager.showNotification("✗ Copy Failed", "error");
    }
  }

  private generatePageStructure(): string {
    const info: PageStructureInfo = {
      url: window.location.href,
      timestamp: new Date().toISOString(),
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
        scrollX: window.scrollX,
        scrollY: window.scrollY,
      },
      document: {
        title: document.title,
        doctype: document.doctype ? document.doctype.name : "none",
        characterSet: document.characterSet,
        readyState: document.readyState,
      },
      structure: this.buildElementTree(document.body, 0, 10),
      stylesheets: this.getAllStylesheets(),
      scripts: this.getAllScripts(),
    };

    return this.formatPageStructureForAI(info);
  }

  private buildElementTree(
    element: Element,
    depth: number,
    maxDepth: number,
  ): any {
    if (depth > maxDepth) {
      return { truncated: true };
    }

    const className =
      typeof element.className === "string" ? element.className : "";
    const node: any = {
      tag: element.tagName.toLowerCase(),
      id: element.id || undefined,
      classes: className ? className.split(/\s+/).filter((c) => c) : undefined,
    };

    const importantAttrs = [
      "href",
      "src",
      "type",
      "name",
      "value",
      "data-*",
      "aria-*",
      "title",
      "alt",
      "placeholder",
      "role",
    ];
    const attrs: any = {};
    for (let i = 0; i < element.attributes.length; i++) {
      const attr = element.attributes[i];
      if (
        importantAttrs.some((pattern) => {
          if (pattern.endsWith("*")) {
            return attr.name.startsWith(pattern.slice(0, -1));
          }
          return attr.name === pattern;
        })
      ) {
        attrs[attr.name] = attr.value;
      }
    }
    if (Object.keys(attrs).length > 0) {
      node.attributes = attrs;
    }

    // Capture direct text content (not from children)
    const textContent = this.getDirectTextContent(element);
    if (textContent) {
      node.text = textContent;
    }

    const children: any[] = [];
    for (let i = 0; i < element.children.length; i++) {
      const child = element.children[i];
      if (child.tagName !== "SCRIPT" && child.tagName !== "STYLE") {
        children.push(this.buildElementTree(child, depth + 1, maxDepth));
      }
    }
    if (children.length > 0) {
      node.children = children;
    }

    return node;
  }

  /**
   * Get direct text content of an element (excluding child element text)
   */
  private getDirectTextContent(element: Element): string | undefined {
    let text = "";
    for (let i = 0; i < element.childNodes.length; i++) {
      const node = element.childNodes[i];
      if (node.nodeType === Node.TEXT_NODE) {
        const trimmed = (node.textContent || "").trim();
        if (trimmed) {
          text += (text ? " " : "") + trimmed;
        }
      }
    }
    // Truncate very long text
    if (text.length > 200) {
      text = text.substring(0, 200) + "...";
    }
    return text || undefined;
  }

  private getAllStylesheets(): any[] {
    const sheets: any[] = [];

    for (let i = 0; i < document.styleSheets.length; i++) {
      try {
        const sheet = document.styleSheets[i];
        const sheetInfo: any = {
          index: i,
          href: sheet.href || "<inline>",
          ruleCount: sheet.cssRules?.length || 0,
        };

        if (sheet.cssRules && sheet.cssRules.length > 0) {
          const sampleRules: string[] = [];
          for (let j = 0; j < Math.min(5, sheet.cssRules.length); j++) {
            sampleRules.push(sheet.cssRules[j].cssText);
          }
          sheetInfo.sampleRules = sampleRules;
        }

        sheets.push(sheetInfo);
      } catch (e) {
        sheets.push({
          index: i,
          href: "<cross-origin or restricted>",
          error: "Cannot access due to CORS",
        });
      }
    }

    return sheets;
  }

  private getAllScripts(): any[] {
    const scripts: any[] = [];
    const scriptElements = document.querySelectorAll("script");

    scriptElements.forEach((script, index) => {
      scripts.push({
        index,
        src: script.src || "<inline>",
        type: script.type || "text/javascript",
        async: script.async,
        defer: script.defer,
      });
    });

    return scripts;
  }

  private formatPageStructureForAI(info: PageStructureInfo): string {
    return `# Full Page Structure

## Page Information
- URL: ${info.url}
- Title: ${info.document.title}
- Timestamp: ${info.timestamp}
- Viewport: ${info.viewport.width}x${info.viewport.height}
- Scroll Position: (${info.viewport.scrollX}, ${info.viewport.scrollY})

## Document Structure
\`\`\`json
${JSON.stringify(info.structure, null, 2)}
\`\`\`

## Stylesheets (${info.stylesheets.length} total)
${info.stylesheets
  .map(
    (s: any, i: number) => `
### ${i + 1}. ${s.href}
- Rules: ${s.ruleCount}
${s.sampleRules ? `- Sample Rules:\n${s.sampleRules.map((r: string) => `  - ${r.substring(0, 100)}...`).join("\n")}` : ""}
${s.error ? `- Error: ${s.error}` : ""}
`,
  )
  .join("\n")}

## Scripts (${info.scripts.length} total)
${info.scripts.map((s: any, i: number) => `${i + 1}. ${s.src} ${s.async ? "[async]" : ""} ${s.defer ? "[defer]" : ""}`).join("\n")}

---
Generated by Element Inspector - Full page structure for AI-assisted debugging.
Press Alt+I to toggle element inspector overlay.
`;
  }
}
