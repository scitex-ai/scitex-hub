/**
 * LaTeX Language Registration
 * Registers LaTeX language with Monaco Editor
 */

import { LatexCompletions } from "./LatexCompletions.js";
import { CitationProvider } from "./CitationProvider.js";

export class LatexLanguage {
  private static citationProvider: CitationProvider;

  /**
   * Register LaTeX language and all providers
   */
  public static register(monaco: any): void {
    console.log(
      "[Monaco] Available languages:",
      monaco.languages.getLanguages().map((l: any) => l.id),
    );

    const latexExists = monaco.languages
      .getLanguages()
      .find((l: any) => l.id === "latex");
    console.log("[Monaco] LaTeX language exists:", !!latexExists);

    if (latexExists) {
      console.log("[Monaco] LaTeX language already registered, skipping");
      return;
    }

    console.log("[Monaco] Registering LaTeX language...");

    // Register language
    monaco.languages.register({ id: "latex" });

    // Set language configuration
    this.setLanguageConfiguration(monaco);

    // Set syntax highlighting
    this.setSyntaxHighlighting(monaco);

    // Register completion providers
    this.registerCompletionProviders(monaco);

    // Register citation providers
    this.citationProvider = new CitationProvider();
    this.citationProvider.register(monaco);
    this.citationProvider.registerHoverProvider(monaco);

    console.log("[Monaco] LaTeX language registration complete");
  }

  /**
   * Set LaTeX language configuration
   */
  private static setLanguageConfiguration(monaco: any): void {
    monaco.languages.setLanguageConfiguration("latex", {
      comments: {
        lineComment: "%",
      },
      brackets: [
        ["{", "}"],
        ["[", "]"],
        ["(", ")"],
        ["\\begin{", "\\end{"],
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
  }

  /**
   * Set LaTeX syntax highlighting
   */
  private static setSyntaxHighlighting(monaco: any): void {
    monaco.languages.setMonarchTokensProvider("latex", {
      tokenizer: {
        root: [
          [/%.*$/, "comment"],
          [/\\[a-zA-Z@]+/, "keyword"],
          [/\{/, "delimiter.curly"],
          [/\}/, "delimiter.curly"],
          [/\[/, "delimiter.square"],
          [/\]/, "delimiter.square"],
          [/\$\$/, "string"],
          [/\$/, "string"],
        ],
      },
    });
  }

  /**
   * Register LaTeX completion providers
   */
  private static registerCompletionProviders(monaco: any): void {
    console.log("[Monaco] Registering LaTeX completion provider...");

    monaco.languages.registerCompletionItemProvider("latex", {
      triggerCharacters: ["\\"],
      provideCompletionItems: (model: any, position: any) => {
        console.log("[Monaco] Completion requested at position:", position);

        const word = model.getWordUntilPosition(position);
        console.log("[Monaco] Word at position:", word);

        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        const suggestions = LatexCompletions.getCompletionItems(monaco);
        const completions = suggestions.map((s: any) => ({
          ...s,
          range,
        }));

        console.log(
          "[Monaco] Returning",
          completions.length,
          "completions",
        );
        return { suggestions: completions };
      },
    });

    console.log(
      "[Monaco] LaTeX completion provider registered successfully",
    );
  }
}
