/**
 * Decorations Manager Module
 * Manages Monaco editor decorations for spelling errors
 */

export class DecorationsManager {
  private decorationsCollection: any;

  constructor(private monaco: any, private editor: any) {
    this.decorationsCollection = this.editor.createDecorationsCollection();
  }

  /**
   * Create decoration options for a misspelled word
   */
  createSpellingDecoration(range: any, word: string): any {
    return {
      range: range,
      options: {
        isWholeLine: false,
        className: 'spell-error',
        glyphMarginClassName: '',
        hoverMessage: { value: `**Spelling**: "${word}" may be misspelled` },
        overviewRuler: {
          color: 'rgba(255, 0, 0, 0.3)',
          position: this.monaco.editor.OverviewRulerLane.Right,
        },
        minimap: {
          color: 'rgba(255, 0, 0, 0.3)',
          position: this.monaco.editor.MinimapPosition.Inline,
        },
        // Red squiggly underline
        inlineClassName: 'spell-error-inline',
      },
    };
  }

  /**
   * Apply decorations to the editor
   */
  setDecorations(decorations: any[]): void {
    this.decorationsCollection.set(decorations);
  }

  /**
   * Clear all decorations
   */
  clearDecorations(): void {
    this.decorationsCollection.clear();
  }

  /**
   * Get decorations collection
   */
  getDecorationsCollection(): any {
    return this.decorationsCollection;
  }
}

/**
 * Add CSS for spell error decorations
 */
export function injectSpellCheckStyles(): void {
  const styleId = 'spell-checker-styles';

  // Check if styles already injected
  if (document.getElementById(styleId)) {
    return;
  }

  const style = document.createElement('style');
  style.id = styleId;
  style.textContent = `
    /* Squiggly underline for spelling errors using theme error color */
    .spell-error-inline {
      background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 6 3" enable-background="new 0 0 6 3" height="3" width="6"><path fill="rgb(192, 136, 136)" d="M5.5,0 Q5.5,3 3,3 T0.5,0"/></svg>');
      background-repeat: repeat-x;
      background-position: left bottom;
      padding-bottom: 2px;
    }
  `;

  document.head.appendChild(style);
  console.log('[SpellChecker] Styles injected');
}
