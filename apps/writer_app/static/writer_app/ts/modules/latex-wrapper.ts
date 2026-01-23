/**
 * LaTeX Wrapper Module
 * Wraps section content with proper LaTeX document structure
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/latex-wrapper.ts loaded",
);
export interface LatexWrapperOptions {
  documentClass?: string;
  packages?: string[];
  preamble?: string;
  title?: string;
  author?: string;
  includeTableOfContents?: boolean;
}

export class LatexWrapper {
  private documentClass: string;
  private packages: string[];
  private preamble: string;
  private title: string;
  private author: string;
  private includeTableOfContents: boolean;

  constructor(options?: LatexWrapperOptions) {
    this.documentClass = options?.documentClass || "article";
    this.packages = options?.packages || this.getDefaultPackages();
    this.preamble = options?.preamble || "";
    this.title = options?.title || "Untitled Manuscript";
    this.author = options?.author || "";
    this.includeTableOfContents = options?.includeTableOfContents ?? true;
  }

  /**
   * Get default LaTeX packages
   */
  private getDefaultPackages(): string[] {
    return [
      "geometry{margin=1in}",
      "graphicx",
      "amsmath",
      "amssymb",
      "hyperref",
      "setspace",
      "natbib",
    ];
  }

  /**
   * Get LaTeX preamble
   */
  getPreamble(): string {
    let preamble = `\\documentclass{${this.documentClass}}\n\n`;

    // Add packages
    this.packages.forEach((pkg) => {
      if (pkg.includes("{")) {
        preamble += `\\usepackage[${pkg}]\n`;
      } else {
        preamble += `\\usepackage{${pkg}}\n`;
      }
    });

    preamble += "\n";

    // Add title and author
    preamble += `\\title{${this.escapeLatexSpecial(this.title)}}\n`;
    if (this.author) {
      preamble += `\\author{${this.escapeLatexSpecial(this.author)}}\n`;
    }

    preamble += "\\date{\\today}\n\n";

    // Add custom preamble
    if (this.preamble) {
      preamble += this.preamble + "\n\n";
    }

    return preamble;
  }

  /**
   * Get LaTeX document begin
   */
  getDocumentBegin(): string {
    let doc = "\\begin{document}\n\n";
    doc += "\\maketitle\n";

    if (this.includeTableOfContents) {
      doc += "\\tableofcontents\n\\newpage\n\n";
    }

    return doc;
  }

  /**
   * Wrap section content with LaTeX structure
   */
  wrapSection(sectionName: string, content: string, level: number = 1): string {
    const sectionCommands = ["section", "subsection", "subsubsection"];
    const command = sectionCommands[Math.min(level, 2)];

    let wrapped = `\\${command}{${this.escapeLatexSpecial(sectionName)}}\n\n`;
    wrapped += content + "\n\n";

    return wrapped;
  }

  /**
   * Wrap multiple sections
   */
  wrapSections(sections: { name: string; content: string }[]): string {
    let content = "";
    sections.forEach((section) => {
      content += this.wrapSection(section.name, section.content, 1);
    });
    return content;
  }

  /**
   * Get LaTeX document end
   */
  getDocumentEnd(): string {
    return "\n\\end{document}\n";
  }

  /**
   * Create complete LaTeX document
   */
  createDocument(sections: { name: string; content: string }[]): string {
    let doc = this.getPreamble();
    doc += this.getDocumentBegin();
    doc += this.wrapSections(sections);
    doc += this.getDocumentEnd();
    return doc;
  }

  /**
   * Escape LaTeX special characters
   */
  private escapeLatexSpecial(text: string): string {
    return text
      .replace(/\\/g, "\\textbackslash{}")
      .replace(/[&%$#_{}]/g, "\\$&")
      .replace(/\^/g, "\\textasciicircum{}")
      .replace(/~/g, "\\textasciitilde{}");
  }

  /**
   * Check if content contains citation commands
   */
  private hasCitations(content: string): boolean {
    // Match \cite{...}, \citep{...}, \citet{...}, \citeauthor{...}, etc.
    const citationPattern = /\\cite[ptaA]?\s*\{[^}]+\}/;
    return citationPattern.test(content);
  }

  /**
   * Create minimal LaTeX document for preview
   */
  createMinimalDocument(content: string, fontSize: number = 11): string {
    // Map editor font size (10-20px) to LaTeX font size (10pt-14pt)
    // 10px -> 10pt, 14px -> 11pt (default), 20px -> 14pt
    const latexFontSize = Math.max(
      10,
      Math.min(14, Math.round(10 + (fontSize - 10) / 2.5)),
    );
    const fontSizeOption = `${latexFontSize}pt`;

    let doc = `\\documentclass[${fontSizeOption}]{article}\n`;
    doc += `\\usepackage{geometry}\n`;
    doc += `\\usepackage[utf8]{inputenc}\n`;
    doc += `\\geometry{margin=1in}\n`;

    // Define bright green color for links using xcolor package
    doc += `\\usepackage{xcolor}\n`;
    doc += `\\definecolor{linkgreen}{RGB}{0,153,0}  % Bright green for visibility\n\n`;

    // Configure hyperref to make links visible with bright green color (alert success color)
    // colorlinks=true: Use colored text for links
    // This colors all hyperlinks green, making them clearly distinguishable from regular text
    doc += `\\usepackage[colorlinks=true,linkcolor=linkgreen,citecolor=linkgreen,urlcolor=linkgreen]{hyperref}\n\n`;

    // Make all links bold for better visibility
    // Redefine citation command to include bold formatting
    doc += `\\let\\oldcite\\cite\n`;
    doc += `\\renewcommand{\\cite}[1]{\\textbf{\\oldcite{#1}}}\n`;
    // Redefine href and url commands to include bold formatting
    doc += `\\let\\oldhref\\href\n`;
    doc += `\\renewcommand{\\href}[2]{\\oldhref{#1}{\\textbf{#2}}}\n`;
    doc += `\\let\\oldurl\\url\n`;
    doc += `\\renewcommand{\\url}[1]{\\textbf{\\oldurl{#1}}}\n\n`;

    doc += `\\begin{document}\n\n`;
    doc += content;

    // Only add bibliography if content contains citations
    // This prevents showing an empty References section
    if (this.hasCitations(content)) {
      doc += `\n\n% Bibliography (automatically included for citation support)\n`;
      doc += `\\bibliographystyle{plain}\n`;
      doc += `\\bibliography{bibliography}\n`;
    }

    doc += `\n\\end{document}\n`;
    return doc;
  }

  /**
   * Set document title
   */
  setTitle(title: string): void {
    this.title = title;
  }

  /**
   * Set document author
   */
  setAuthor(author: string): void {
    this.author = author;
  }

  /**
   * Add package to preamble
   */
  addPackage(packageName: string): void {
    if (!this.packages.includes(packageName)) {
      this.packages.push(packageName);
    }
  }

  /**
   * Remove package from preamble
   */
  removePackage(packageName: string): void {
    const index = this.packages.indexOf(packageName);
    if (index > -1) {
      this.packages.splice(index, 1);
    }
  }
}
