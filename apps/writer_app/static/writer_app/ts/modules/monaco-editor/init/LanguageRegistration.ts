/**
 * Language Registration Module
 * Handles LaTeX language registration with Monaco Editor
 */

console.log("[DEBUG] LanguageRegistration.ts loaded");

/**
 * Register LaTeX language with Monaco
 */
export function registerLatexLanguage(monaco: any): void {
  const latexExists = monaco.languages
    .getLanguages()
    .find((l: any) => l.id === "latex");
  console.log("[Monaco] LaTeX language exists:", !!latexExists);

  if (latexExists) {
    console.log("[Monaco] LaTeX language already registered, skipping");
    return;
  }

  console.log("[Monaco] Registering LaTeX language...");
  monaco.languages.register({ id: "latex" });

  // Define LaTeX language configuration
  monaco.languages.setLanguageConfiguration("latex", {
    comments: {
      lineComment: "%",
    },
    brackets: [
      ["{", "}"],
      ["[", "]"],
      ["(", ")"],
      ["\\begin{", "\\end{"], // Treat LaTeX environments as bracket pairs!
    ],
    autoClosingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: "$", close: "$" },
      { open: "`", close: "'" },
      { open: "\\begin{", close: "}", notIn: ["string", "comment"] },
    ],
    surroundingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: "$", close: "$" },
    ],
  });

  // Define LaTeX syntax highlighting with comprehensive Monarch grammar
  monaco.languages.setMonarchTokensProvider("latex", {
    defaultToken: "",
    tokenPostfix: ".latex",

    // LaTeX commands that start environments
    environments: [
      "document", "abstract", "equation", "align", "gather", "multline",
      "figure", "table", "tabular", "itemize", "enumerate", "description",
      "verbatim", "lstlisting", "quote", "quotation", "verse", "center",
      "flushleft", "flushright", "minipage", "array", "matrix", "cases",
      "theorem", "lemma", "proof", "definition", "corollary", "remark"
    ],

    tokenizer: {
      root: [
        // Comments
        [/%.*$/, "comment.latex"],

        // Math mode - display math ($$...$$)
        [/\$\$/, { token: "string.math.latex", next: "@displayMath" }],

        // Math mode - inline math ($...$)
        [/\$/, { token: "string.math.latex", next: "@inlineMath" }],

        // Environment begin/end
        [/(\\begin)(\{)([a-zA-Z*]+)(\})/, [
          "keyword.control.latex",
          "delimiter.curly.latex",
          "type.identifier.latex",
          "delimiter.curly.latex"
        ]],
        [/(\\end)(\{)([a-zA-Z*]+)(\})/, [
          "keyword.control.latex",
          "delimiter.curly.latex",
          "type.identifier.latex",
          "delimiter.curly.latex"
        ]],

        // Section commands (with special highlighting)
        [/\\(section|subsection|subsubsection|paragraph|chapter|part)\b/, "keyword.section.latex"],

        // Common commands
        [/\\[a-zA-Z@]+\*?/, "keyword.latex"],

        // Arguments in braces
        [/\{/, "delimiter.curly.latex"],
        [/\}/, "delimiter.curly.latex"],

        // Optional arguments in brackets
        [/\[/, "delimiter.square.latex"],
        [/\]/, "delimiter.square.latex"],

        // Numbers
        [/\d+/, "number.latex"],

        // Special characters
        [/[&~^_]/, "operator.latex"],
      ],

      // Display math mode ($$...$$)
      displayMath: [
        [/\$\$/, { token: "string.math.latex", next: "@pop" }],
        [/\\[a-zA-Z@]+/, "keyword.math.latex"],
        [/./, "string.math.latex"],
      ],

      // Inline math mode ($...$)
      inlineMath: [
        [/\$/, { token: "string.math.latex", next: "@pop" }],
        [/\\[a-zA-Z@]+/, "keyword.math.latex"],
        [/./, "string.math.latex"],
      ],
    },
  });

  console.log("[Monaco] LaTeX language registered with syntax highlighting");
}
