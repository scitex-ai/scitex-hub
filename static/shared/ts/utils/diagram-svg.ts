/** Safe diagram publication: inert images, or a resource-free interactive SVG. */
import DOMPurify from "dompurify";

export function appendSvgImage(wrapper: HTMLElement, svg: string, alt: string): void {
  const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml;charset=utf-8" }));
  const image = document.createElement("img");
  image.src = url;
  image.alt = alt;
  image.className = "stx-shell-ai-media-diagram-image";
  image.style.maxWidth = "100%";
  image.style.height = "auto";
  const revoke = () => URL.revokeObjectURL(url);
  image.addEventListener("load", revoke, { once: true });
  image.addEventListener("error", revoke, { once: true });
  wrapper.replaceChildren(image);
}

function safeDeclaration(name: string, value: string, ids: Set<string>): boolean {
  if (["fill", "stroke", "color", "stop-color"].includes(name)) {
    return value === "none" || (!/(?:url|var|env|expression)\s*\(|\\/i.test(value) && CSS.supports("color", value));
  }
  if (["marker-start", "marker-mid", "marker-end", "clip-path", "filter"].includes(name)) {
    if (value === "none") return true;
    const match = /^url\(["']?#([\w:-]+)["']?\)$/.exec(value);
    return !!match && ids.has(match[1]);
  }
  if (["opacity", "fill-opacity", "stroke-opacity"].includes(name)) {
    return /^(?:0(?:\.\d+)?|1(?:\.0+)?)$/.test(value);
  }
  if (["font-size", "stroke-width", "letter-spacing", "width", "height", "max-width", "max-height"].includes(name)) {
    return /^\d+(?:\.\d+)?(?:px|pt|em|rem|%)?$/.test(value);
  }
  if (name === "stroke-dasharray") return /^[\d.,\s]+$/.test(value) || value === "none";
  if (name === "font-family") return /^[\w\s,\-"']+$/.test(value);
  const enums: Record<string, string[]> = {
    "font-weight": ["normal", "bold", "100", "200", "300", "400", "500", "600", "700", "800", "900"],
    "font-style": ["normal", "italic", "oblique"],
    "text-anchor": ["start", "middle", "end"],
    "dominant-baseline": ["auto", "middle", "central", "hanging", "alphabetic"],
    "stroke-linecap": ["butt", "round", "square"],
    "stroke-linejoin": ["miter", "round", "bevel"],
    "white-space": ["normal", "pre", "pre-wrap"],
  };
  return enums[name]?.includes(value) ?? false;
}

function applyDeclarations(element: SVGElement, style: CSSStyleDeclaration, ids: Set<string>): void {
  for (let index = 0; index < style.length; index++) {
    const name = style.item(index);
    const value = style.getPropertyValue(name).trim();
    if (safeDeclaration(name, value, ids)) element.style.setProperty(name, value);
  }
}

/** Keep Clew node clicks without admitting executable SVG or external resources. */
export function interactiveSvg(text: string): SVGSVGElement {
  const fragment = DOMPurify.sanitize(text, {
    USE_PROFILES: { svg: true, svgFilters: true },
    RETURN_DOM_FRAGMENT: true,
    FORBID_TAGS: ["script", "foreignObject", "a", "image", "use", "animate", "animateMotion", "animateTransform", "set", "feImage"],
    FORBID_ATTR: ["href", "xlink:href", "src"],
  });
  const svg = fragment.querySelector("svg");
  if (!(svg instanceof SVGSVGElement)) throw new Error("Diagram contains no SVG");
  const ids = new Set(Array.from(svg.querySelectorAll("[id]"), element => element.id));
  ids.add(svg.id);
  const elements = [svg, ...svg.querySelectorAll<SVGElement>("*")];
  const inline = elements.map(element => [element, element.getAttribute("style")] as const);
  const styles = Array.from(svg.querySelectorAll("style"), element => element.textContent ?? "");
  svg.querySelectorAll("style").forEach(element => element.remove());
  for (const element of elements) {
    element.removeAttribute("style");
    for (const name of ["fill", "stroke", "filter", "clip-path", "marker-start", "marker-mid", "marker-end"]) {
      const value = element.getAttribute(name);
      if (value !== null && !safeDeclaration(name, value, ids)) element.removeAttribute(name);
    }
  }
  // Native CSSOM parses styles off-document. No stylesheet is ever adopted;
  // only explicitly admitted declarations are applied inside this SVG subtree.
  for (const text of styles) {
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(text);
    for (const rule of sheet.cssRules) {
      if (!(rule instanceof CSSStyleRule)) continue;
      try {
        if (svg.matches(rule.selectorText)) applyDeclarations(svg, rule.style, ids);
        for (const element of svg.querySelectorAll<SVGElement>(rule.selectorText)) {
          applyDeclarations(element, rule.style, ids);
        }
      } catch { /* Malformed/unsupported selectors confer no styling. */ }
    }
  }
  for (const [element, text] of inline) {
    if (!text) continue;
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(`x { ${text} }`);
    const rule = sheet.cssRules[0];
    if (rule instanceof CSSStyleRule) applyDeclarations(element, rule.style, ids);
  }
  return svg;
}
