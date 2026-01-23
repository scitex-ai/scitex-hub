/**
 * LaTeX Completion Items
 * Provides autocomplete suggestions for LaTeX commands
 */

export class LatexCompletions {
  /**
   * Get all LaTeX completion items
   */
  public static getCompletionItems(monaco: any): any[] {
    return [
      // Document structure
      {
        label: "\\documentclass",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\documentclass{article}",
        documentation: "Document class",
      },
      {
        label: "\\begin",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText:
          "\\begin{${1:environment}}\n\t$0\n\\end{${1:environment}}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Begin environment",
      },
      {
        label: "\\end",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\end{${1:environment}}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "End environment",
      },
      {
        label: "\\section",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\section{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Section",
      },
      {
        label: "\\subsection",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\subsection{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Subsection",
      },
      {
        label: "\\subsubsection",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\subsubsection{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Subsubsection",
      },

      // Text formatting
      {
        label: "\\textbf",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\textbf{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Bold text",
      },
      {
        label: "\\textit",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\textit{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Italic text",
      },
      {
        label: "\\emph",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\emph{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Emphasized text",
      },
      {
        label: "\\texttt",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\texttt{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Typewriter text",
      },

      // Math mode
      {
        label: "\\[",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\[\n\t$0\n\\]",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Display math",
      },
      {
        label: "\\(",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\($0\\)",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Inline math",
      },
      {
        label: "\\equation",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\begin{equation}\n\t$0\n\\end{equation}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Equation environment",
      },

      // Figures and tables
      {
        label: "\\figure",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText:
          "\\begin{figure}[htbp]\n\t\\centering\n\t\\includegraphics[width=0.8\\textwidth]{$1}\n\t\\caption{$2}\n\t\\label{fig:$3}\n\\end{figure}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Figure environment",
      },
      {
        label: "\\table",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText:
          "\\begin{table}[htbp]\n\t\\centering\n\t\\caption{$1}\n\t\\label{tab:$2}\n\t\\begin{tabular}{$3}\n\t\t$0\n\t\\end{tabular}\n\\end{table}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Table environment",
      },

      // Citations and references
      {
        label: "\\cite",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\cite{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Citation",
      },
      {
        label: "\\ref",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\ref{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Reference",
      },
      {
        label: "\\label",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\label{$0}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Label",
      },

      // Lists
      {
        label: "\\itemize",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\begin{itemize}\n\t\\item $0\n\\end{itemize}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Itemize list",
      },
      {
        label: "\\enumerate",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\begin{enumerate}\n\t\\item $0\n\\end{enumerate}",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "Enumerate list",
      },
      {
        label: "\\item",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "\\item $0",
        insertTextRules:
          monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: "List item",
      },
    ];
  }
}
