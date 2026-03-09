# Spell Checker - Quick Start

## ✅ What Was Added

Two files were created/modified to add spell checking to Monaco Editor:

1. **`spell-checker.ts`** - Complete spell checker module (~500 lines)
2. **`monaco-editor.ts`** - Updated to integrate spell checker

## 🚀 How to Test

### 1. Wait for Auto-Build

The TypeScript watch mechanism will automatically compile:
- `spell-checker.ts` → `spell-checker.js`
- `monaco-editor.ts` → `monaco-editor.js` (updated)

### 2. Reload the Page

Visit: http://127.0.0.1:8000/writer/

### 3. Type Some Text

Try typing in the Monaco editor:

```
This is a test sentense with some mispeled words.
The algorythm will detect erors in realtime.
```

You should see **red squiggly underlines** under:
- "sentense" (should be "sentence")
- "mispeled" (should be "misspelled")
- "algorythm" (should be "algorithm")
- "erors" (should be "errors")

### 4. LaTeX Commands Are Skipped

Try typing LaTeX:

```latex
\section{Introduction}
This is a test with $x^2$ math mode.
\cite{smith2020}
```

The spell checker will:
- ✅ Skip `\section`, `\cite`, and math mode
- ✅ Only check regular English text
- ✅ Ignore LaTeX commands

### 5. Add Words to Dictionary

Right-click on a "misspelled" word and select **"Add to dictionary"**

The word will be saved to localStorage and won't be marked as an error anymore.

## 🎮 Browser Console Commands

Open the browser console (F12) and try:

```javascript
// Get the editor instance
const editorModule = await import('/static/writer_app/js/modules/monaco-editor.js');

// Disable spell checking
editor.disableSpellCheck();

// Enable spell checking
editor.enableSpellCheck();

// Add word to dictionary
editor.addToSpellCheckDictionary('neuroscience');

// Clear dictionary
editor.clearSpellCheckDictionary();
```

## 📊 Console Output

Watch the browser console for debug messages:

```
[SpellChecker] Initialized with config: {...}
[SpellChecker] Enabled
[SpellChecker] Found 3 potential spelling errors
[SpellChecker] Added "neuroscience" to custom dictionary
```

## 🔧 Current Dictionary

The spell checker currently uses a **basic English dictionary** (~200 common words) including:
- Common words (the, is, was, etc.)
- Academic words (research, study, data, analysis, etc.)
- LaTeX terms (latex, document, bibliography, etc.)

## 📝 Known Limitations

1. **Basic Dictionary**: Only ~200 words are included for demonstration
   - **Solution**: Integrate Typo.js or Nspell for full English dictionary
   - See `SPELL_CHECKER_README.md` for integration instructions

2. **No Suggestions Yet**: Right-click menu only shows "Add to dictionary"
   - **Solution**: Implement suggestion algorithm with edit distance

3. **Single Language**: Only English is supported
   - **Solution**: Add multi-language support with language detection

## 🐛 Troubleshooting

### No red underlines appear

1. **Check console for errors**
   ```javascript
   // Browser console (F12)
   ```

2. **Verify spell checker is loaded**
   ```javascript
   console.log('[Check]', typeof SpellChecker);
   // Should output: [Check] function
   ```

3. **Check if enabled**
   ```javascript
   // Should see: [SpellChecker] Enabled
   ```

### 404 Error for spell-checker.js

- **Issue**: Module import path missing `.js` extension
- **Fixed**: Updated import to use `./spell-checker.js`

### Words not marked as errors

- This is expected! The current dictionary is intentionally **permissive**
- To make it stricter, edit `checkWordWithBrowser()` in `spell-checker.ts`

## 🎯 Next Steps

### For Production Use

1. **Integrate Real Dictionary** (see `SPELL_CHECKER_README.md`)
   ```bash
   npm install typo-js
   ```

2. **Add Spelling Suggestions**
   - Implement Levenshtein distance algorithm
   - Show top 3 suggestions in quick-fix menu

3. **Multi-language Support**
   - Detect language from LaTeX `\documentclass[lang]{...}`
   - Load appropriate dictionary

4. **Performance Optimization**
   - Move to Web Worker for large documents
   - Implement viewport-only checking

## 📚 Documentation

- **Full docs**: `SPELL_CHECKER_README.md`
- **API reference**: See README for complete API
- **Integration guide**: Instructions for Typo.js/Nspell integration

## ✨ Features Summary

✅ Red squiggly underlines
✅ LaTeX-aware (skips commands, math, citations)
✅ Custom dictionary with localStorage persistence
✅ Debounced checking (500ms)
✅ Fast caching
✅ Right-click to add words
✅ Enable/disable on demand

## 🎉 You're Done!

The spell checker is now integrated and ready to use. Just reload the page and start typing!
