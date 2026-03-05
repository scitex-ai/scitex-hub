/**
 * Local Monaco Editor Initialization
 *
 * Single source of truth for Monaco loading. All consumers (viewer, writer,
 * console) import from here. Monaco is bundled locally via npm — no CDN.
 *
 * Workers run on the main thread (fake worker) to avoid CORS/bundling
 * complexity. This is fine because Monaco workers only provide language
 * services (JS/TS/CSS validation) which we don't need for LaTeX/BibTeX.
 */

import * as monaco from "monaco-editor";

// Import Monaco CSS so Vite bundles it automatically
import "monaco-editor/min/vs/editor/editor.main.css";

// ── Worker environment (main-thread fallback) ────────────────────────

interface FakeWorker {
  postMessage: () => void;
  terminate: () => void;
  addEventListener: () => void;
  removeEventListener: () => void;
}

function createFakeWorker(): FakeWorker {
  return {
    postMessage: () => {},
    terminate: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
  };
}

(self as any).MonacoEnvironment = {
  getWorker(_moduleId: string, _label: string): FakeWorker {
    return createFakeWorker();
  },
};

// ── Custom language registration ─────────────────────────────────────

function registerCustomLanguages(): void {
  // LaTeX
  if (!monaco.languages.getLanguages().find((l) => l.id === "latex")) {
    monaco.languages.register({
      id: "latex",
      extensions: [".tex", ".sty", ".cls", ".ltx"],
    });
    monaco.languages.setLanguageConfiguration("latex", {
      comments: { lineComment: "%" },
      brackets: [
        ["{", "}"],
        ["[", "]"],
        ["(", ")"],
      ],
      autoClosingPairs: [
        { open: "{", close: "}" },
        { open: "[", close: "]" },
        { open: "(", close: ")" },
        { open: "$", close: "$" },
      ],
      surroundingPairs: [
        { open: "{", close: "}" },
        { open: "[", close: "]" },
        { open: "(", close: ")" },
        { open: "$", close: "$" },
      ],
    });
    monaco.languages.setMonarchTokensProvider("latex", {
      defaultToken: "",
      tokenPostfix: ".latex",
      tokenizer: {
        root: [
          [/%.*$/, "comment"],
          [/\$\$/, { token: "string", next: "@displayMath" }],
          [/\$/, { token: "string", next: "@inlineMath" }],
          [
            /(\\begin)(\{)([a-zA-Z*]+)(\})/,
            ["keyword", "delimiter.curly", "type", "delimiter.curly"],
          ],
          [
            /(\\end)(\{)([a-zA-Z*]+)(\})/,
            ["keyword", "delimiter.curly", "type", "delimiter.curly"],
          ],
          [
            /\\(section|subsection|subsubsection|paragraph|chapter|part)\b/,
            "keyword",
          ],
          [/\\[a-zA-Z@]+\*?/, "keyword"],
          [/\{/, "delimiter.curly"],
          [/\}/, "delimiter.curly"],
          [/\[/, "delimiter.square"],
          [/\]/, "delimiter.square"],
          [/\d+/, "number"],
          [/[&~^_]/, "operator"],
        ],
        displayMath: [
          [/\$\$/, { token: "string", next: "@pop" }],
          [/\\[a-zA-Z@]+/, "keyword"],
          [/./, "string"],
        ],
        inlineMath: [
          [/\$/, { token: "string", next: "@pop" }],
          [/\\[a-zA-Z@]+/, "keyword"],
          [/./, "string"],
        ],
      },
    });
    console.log("[Monaco] Registered LaTeX language");
  }

  // BibTeX
  if (!monaco.languages.getLanguages().find((l) => l.id === "bibtex")) {
    monaco.languages.register({ id: "bibtex", extensions: [".bib"] });
    monaco.languages.setMonarchTokensProvider("bibtex", {
      defaultToken: "",
      tokenPostfix: ".bibtex",
      tokenizer: {
        root: [
          [/%.*$/, "comment"],
          [/@[a-zA-Z]+/, "keyword"],
          [/\{/, "delimiter.curly"],
          [/\}/, "delimiter.curly"],
          [/=/, "operator"],
          [/"[^"]*"/, "string"],
          [/\d+/, "number"],
        ],
      },
    });
    console.log("[Monaco] Registered BibTeX language");
  }
}

// ── Initialize ───────────────────────────────────────────────────────

registerCustomLanguages();

// Set globals for backward compatibility (many files check window.monaco)
(window as any).monaco = monaco;
(window as any).monacoReady = true;
(window as any).monacoLoaded = true;
window.dispatchEvent(new Event("monaco-ready"));

console.log("[Monaco] Initialized from local bundle");

// ── Exports ──────────────────────────────────────────────────────────

export { monaco };
export default monaco;
