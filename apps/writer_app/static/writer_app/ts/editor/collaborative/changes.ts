/**
 * Change Tracking and Word Count Management
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

import type { ManuscriptConfig } from "./types.js";

export class ChangeTracker {
  constructor(private manuscriptConfig: ManuscriptConfig) {}

  /**
   * Count words in a text string
   */
  countWords(text: string): number {
    return text
      .trim()
      .split(/\s+/)
      .filter((word) => word.length > 0).length;
  }

  /**
   * Update word count for a specific section
   */
  updateWordCount(section: string): void {
    const textarea = document.getElementById(
      `section-${section}`,
    ) as HTMLTextAreaElement;
    const countElement = document.getElementById(`${section}-count`);

    if (textarea && countElement) {
      const wordCount = this.countWords(textarea.value);
      countElement.textContent = `${wordCount} words`;
    }
  }

  /**
   * Update word counts for all sections
   */
  updateWordCounts(): void {
    this.manuscriptConfig.sections.forEach((section) => {
      this.updateWordCount(section);
    });
  }

  /**
   * Update overall progress indicators
   */
  updateProgress(): void {
    let totalWords = 0;
    let sectionsCompleted = 0;

    this.manuscriptConfig.sections.forEach((section) => {
      const textarea = document.getElementById(
        `section-${section}`,
      ) as HTMLTextAreaElement;
      if (textarea) {
        const wordCount = this.countWords(textarea.value);
        totalWords += wordCount;
        if (wordCount > 0) sectionsCompleted++;
      }
    });

    const completionPercentage = Math.round(
      (sectionsCompleted / this.manuscriptConfig.sections.length) * 100,
    );

    // Update progress display
    const totalWordsEl = document.getElementById("total-words");
    const sectionsCompletedEl = document.getElementById("sections-completed");
    const completionPercentageEl = document.getElementById(
      "completion-percentage",
    );

    if (totalWordsEl) totalWordsEl.textContent = String(totalWords);
    if (sectionsCompletedEl) {
      sectionsCompletedEl.textContent = `${sectionsCompleted}/${this.manuscriptConfig.sections.length}`;
    }
    if (completionPercentageEl) {
      completionPercentageEl.textContent = `${completionPercentage}%`;
    }
  }

  /**
   * Mark document as modified (visual indicator)
   */
  markAsModified(): void {
    // Visual indication that document has unsaved changes
    if (!document.title.startsWith("● ")) {
      document.title = "● " + document.title;
    }
  }
}
