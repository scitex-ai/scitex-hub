# Monaco Editor Spell Checker

A lightweight, intelligent spell checker for Monaco Editor that's specifically designed for LaTeX documents.

## Features

### ✅ What It Does

1. **Red Squiggly Underlines** - Shows spelling errors with red wavy underlines (like VS Code)
2. **Smart LaTeX Awareness** - Automatically skips:
   - LaTeX commands (`\section`, `\textbf`, etc.)
   - Math mode (`$...$`, `$$...$$`, `\begin{equation}...\end{equation}`)
   - Citations (`\cite{...}`, `\citep{...}`)
   - References (`\ref{...}`, `\label{...}`)
3. **Custom Dictionary** - Add frequently used technical terms to a personal dictionary
4. **Fast & Lightweight** - Debounced checking (500ms) with caching
5. **Quick Fixes** - Right-click on errors to add words to dictionary

### 🎯 Use Cases

- Writing scientific papers in LaTeX
- Technical documentation with specialized terminology
- Collaborative writing where custom terms are common

## How It Works

### Initialization

The spell checker is automatically initialized when Monaco Editor starts:

```typescript
// In monaco-editor.ts
this.spellChecker = new SpellChecker(monaco, this.monacoEditor, {
  enabled: true,
  language: 'en-US',
  skipLaTeXCommands: true,
  skipMathMode: true,
  skipCodeBlocks: true,
});
this.spellChecker.loadCustomDictionary();
this.spellChecker.enable();
```

### Text Processing Pipeline

1. **Extract Checkable Regions** - Identifies text that should be spell-checked
   - Builds skip ranges for LaTeX commands, math, citations
   - Merges overlapping ranges
   - Extracts remaining text regions

2. **Word Extraction** - Finds individual words to check
   - Matches words with regex: `/\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b/g`
   - Supports contractions (don't, it's, etc.)
   - Skips very short words (≤ 2 chars)
   - Skips proper nouns (capitalized words)

3. **Spell Checking** - Validates each word
   - Checks custom dictionary first
   - Uses cache for performance
   - Falls back to browser API (placeholder for now)

4. **Visual Feedback** - Shows errors inline
   - Red squiggly underline decoration
   - Hover tooltip with error message
   - Minimap and overview ruler markers

### Custom Dictionary

Words are stored in `localStorage` under key `scitex_custom_dictionary`:

```typescript
// Add a word
editor.addToSpellCheckDictionary('neuroscience');

// Clear dictionary
editor.clearSpellCheckDictionary();
```

Dictionary persists across sessions.

## API Reference

### EnhancedEditor Methods

```typescript
// Enable/disable spell checking
editor.enableSpellCheck();
editor.disableSpellCheck();

// Manage custom dictionary
editor.addToSpellCheckDictionary(word: string);
editor.clearSpellCheckDictionary();
```

### SpellChecker Class

```typescript
constructor(monaco: any, editor: any, config?: Partial<SpellCheckConfig>)

interface SpellCheckConfig {
  enabled: boolean;           // Enable spell checking
  language: string;           // e.g., 'en-US', 'en-GB'
  skipLaTeXCommands: boolean; // Skip \command
  skipMathMode: boolean;      // Skip $...$ and $$...$$
  skipCodeBlocks: boolean;    // Skip code environments
  customDictionary?: string[]; // Initial custom words
}

// Methods
enable(): void                          // Start checking
disable(): void                         // Stop checking
addToCustomDictionary(word: string): void  // Add word
clearCustomDictionary(): void           // Clear all custom words
loadCustomDictionary(): void            // Load from localStorage
```

## Integration with External Spell Checkers

The current implementation uses a **placeholder** for actual spell checking (`checkWordWithBrowser` always returns `true`). To integrate a real spell checker:

### Option 1: Typo.js (Hunspell-based)

```bash
npm install typo-js
```

```typescript
import Typo from 'typo-js';

private dictionary: Typo | null = null;

async initDictionary() {
  const affData = await fetch('/static/dictionaries/en_US.aff').then(r => r.text());
  const dicData = await fetch('/static/dictionaries/en_US.dic').then(r => r.text());
  this.dictionary = new Typo('en_US', affData, dicData);
}

private async checkWordWithBrowser(word: string): Promise<boolean> {
  if (!this.dictionary) return true;
  return this.dictionary.check(word);
}
```

### Option 2: Nspell (Fast, streaming)

```bash
npm install nspell
```

```typescript
import nspell from 'nspell';

private spell: any;

async initSpell() {
  const aff = await fetch('/static/dictionaries/en_US.aff').then(r => r.text());
  const dic = await fetch('/static/dictionaries/en_US.dic').then(r => r.text());
  this.spell = nspell({ aff, dic });
}

private async checkWordWithBrowser(word: string): Promise<boolean> {
  return this.spell.correct(word);
}
```

### Option 3: Browser Native API (Experimental)

```typescript
private async checkWordWithBrowser(word: string): Promise<boolean> {
  // Note: This API is not widely supported yet
  if ('spellingAPI' in navigator) {
    const results = await (navigator as any).spellingAPI.spellcheck(word);
    return results.length === 0;
  }
  return true;
}
```

## Performance Considerations

- **Debouncing**: 500ms delay before checking (adjustable)
- **Caching**: Previously checked words are cached
- **Incremental**: Only checks visible content
- **Skip Patterns**: Regex patterns compiled once at initialization

## CSS Styling

Red squiggly underline is added via SVG background:

```css
.spell-error-inline {
  background-image: url('data:image/svg+xml;utf8,<svg>...</svg>');
  background-repeat: repeat-x;
  background-position: left bottom;
  padding-bottom: 2px;
}
```

## Future Enhancements

1. **Spelling Suggestions** - Show correction options in quick-fix menu
2. **Multi-language Support** - Detect and switch languages automatically
3. **Grammar Checking** - Basic grammar rules (e.g., LanguageTool integration)
4. **Ignore Patterns** - User-defined regex patterns to skip
5. **Dictionary Sync** - Sync custom dictionary across devices
6. **Performance** - Web Worker for large documents

## Troubleshooting

### No red underlines appear

1. Check console for errors
2. Verify spell checker is enabled: `editor.enableSpellCheck()`
3. Check if styles are injected: Look for `#spell-checker-styles` in DOM

### Too many false positives

1. Add technical terms to custom dictionary
2. Adjust skip patterns in `extractCheckableRegions()`
3. Consider using a specialized dictionary (medical, scientific, etc.)

### Slow performance on large documents

1. Increase debounce delay
2. Reduce visible suggestions count
3. Consider lazy loading (only check visible viewport)

## License

Part of the SciTeX project.
