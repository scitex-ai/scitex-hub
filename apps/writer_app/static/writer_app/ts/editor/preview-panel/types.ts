/**
 * Preview Panel Type Definitions
 * Shared types and interfaces for the preview panel system
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/editor/preview-panel/types.ts loaded",
);

export interface CompilationData {
  content: string;
  title: string;
}

export interface CompilationResponse {
  success: boolean;
  job_id?: string;
  error?: string;
}

export interface CompilationStatus {
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  pdf_url?: string;
  error?: string;
}

export interface LatexTemplates {
  [key: string]: string;
}

export interface PreviewPanelConfig {
  quickCompileUrl: string;
  compilationStatusUrl: string;
  csrfToken: string;
}

/**
 * LaTeX Templates
 */
export const LATEX_TEMPLATES: LatexTemplates = {
  article: `\\documentclass[12pt]{article}
\\usepackage[utf8]{inputenc}
\\usepackage{amsmath}
\\usepackage{graphicx}
\\usepackage[margin=1in]{geometry}
\\usepackage{cite}

\\title{Your Article Title}
\\author{Your Name\\\\Your Institution}
\\date{\\today}

\\begin{document}

\\maketitle

\\begin{abstract}
Write your abstract here...
\\end{abstract}

\\section{Introduction}
Introduction content...

\\section{Related Work}
Related work...

\\section{Methodology}
Methodology...

\\section{Results}
Results...

\\section{Conclusion}
Conclusion...

\\bibliographystyle{plain}
\\bibliography{references}

\\end{document}`,

  conference: `\\documentclass[conference]{IEEEtran}
\\usepackage{amsmath}
\\usepackage{graphicx}
\\usepackage{cite}

\\title{Your Conference Paper Title}
\\author{\\IEEEauthorblockN{Your Name}
\\IEEEauthorblockA{Your Institution\\\\
Email: your.email@institution.edu}}

\\begin{document}

\\maketitle

\\begin{abstract}
Abstract content...
\\end{abstract}

\\section{Introduction}
Introduction...

\\section{Methodology}
Methodology...

\\section{Results}
Results...

\\section{Conclusion}
Conclusion...

\\begin{thebibliography}{1}
\\bibitem{ref1}
Author, "Title," Journal, Year.
\\end{thebibliography}

\\end{document}`,

  letter: `\\documentclass{letter}
\\usepackage[margin=1in]{geometry}

\\signature{Your Name}
\\address{Your Address\\\\City, State ZIP}

\\begin{document}

\\begin{letter}{Recipient Name\\\\
Recipient Address\\\\
City, State ZIP}

\\opening{Dear Recipient,}

Body of the letter goes here...

\\closing{Sincerely,}

\\end{letter}

\\end{document}`,
};
