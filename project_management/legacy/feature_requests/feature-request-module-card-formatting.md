# Feature Request: Left-Align Module Card Descriptions with Bullet Points

**Date**: 2025-05-23
**Priority**: High
**Category**: UI/UX Improvement

## Summary

Update the module card descriptions on the landing page to use left-aligned bullet points instead of centered text with line breaks. This will improve readability and create a cleaner, more professional appearance.

## Current Issue

The current module descriptions use `<br>` tags and center alignment:
```html
<p>
  Powered by Claude Code agent<br>
  Sets of guidelines and commands<br>
  Human-in-the-loop system on Emacs
</p>
```

This creates:
- Difficult to scan text
- Inconsistent line lengths
- Less professional appearance
- Poor alignment on mobile devices

## Proposed Solution

### HTML Structure Update

Replace paragraph text with unordered lists:

```html
<!-- Current -->
<p>
  AI-powered research environment<br>
  Intelligent coding assistance<br>
  Seamless Emacs integration
</p>

<!-- Proposed -->
<ul class="module-features">
  <li>AI-powered research environment</li>
  <li>Intelligent coding assistance</li>
  <li>Seamless Emacs integration</li>
</ul>
```

### CSS Styling

```css
.product-card {
  text-align: left; /* Change from center */
}

.product-card h3 {
  text-align: center; /* Keep title centered */
  margin-bottom: 1rem;
}

.module-features {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: left;
}

.module-features li {
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: 0.5rem;
  color: var(--text-color);
  line-height: 1.5;
}

.module-features li:before {
  content: "•";
  position: absolute;
  left: 0;
  color: var(--scitex-color-04);
  font-weight: bold;
}

/* Alternative: Use checkmarks instead of bullets */
.module-features.checkmarks li:before {
  content: "✓";
  color: var(--success-color);
}
```

## Updated Module Descriptions

### SciTeX Studio (Engine)
```html
<ul class="module-features">
  <li>AI-powered research environment</li>
  <li>Intelligent coding assistance</li>
  <li>Seamless Emacs integration</li>
</ul>
```

### SciTeX Manuscript (Doc)
```html
<ul class="module-features">
  <li>AI-enhanced scientific writing</li>
  <li>Modular LaTeX workflow</li>
  <li>Smart citation management</li>
</ul>
```

### SciTeX Discover (Search)
```html
<ul class="module-features">
  <li>Comprehensive literature discovery</li>
  <li>Research gap analysis</li>
  <li>Hypothesis generation</li>
</ul>
```

### SciTeX Compute (Code)
```html
<ul class="module-features">
  <li>Advanced data analysis</li>
  <li>Machine learning pipelines</li>
  <li>Statistical computing</li>
</ul>
```

### SciTeX Figures (Viz)
```html
<ul class="module-features">
  <li>Publication-quality graphics</li>
  <li>Professional data visualization</li>
  <li>VisPlot integration</li>
</ul>
```

### SciTeX Cloud
```html
<ul class="module-features">
  <li>Unified research platform</li>
  <li>Scalable computing resources</li>
  <li>Team collaboration tools</li>
</ul>
```

## Visual Comparison

### Before (Current)
```
┌─────────────────────┐
│    SciTeX Studio    │
│                     │
│  Powered by Claude  │
│   Code agent Sets   │
│  of guidelines and  │
│      commands       │
│                     │
└─────────────────────┘
```

### After (Proposed)
```
┌─────────────────────┐
│    SciTeX Studio    │
│                     │
│ • AI-powered research│
│   environment       │
│ • Intelligent coding│
│   assistance        │
│ • Seamless Emacs    │
│   integration       │
└─────────────────────┘
```

## Benefits

1. **Improved Readability**: Bullet points are easier to scan
2. **Professional Appearance**: Standard UI pattern for feature lists
3. **Better Mobile Experience**: Left-aligned text works better on small screens
4. **Consistent Spacing**: Lists handle spacing automatically
5. **Flexibility**: Easy to add/remove features

## Implementation Steps

1. Update HTML structure in `landing.html`
2. Add CSS styles to `landing.css`
3. Test on various screen sizes
4. Ensure GitHub buttons still align properly

## Alternative Designs

### Option A: Icons + Text
```html
<ul class="module-features with-icons">
  <li><i class="fas fa-brain"></i> AI-powered environment</li>
  <li><i class="fas fa-code"></i> Intelligent assistance</li>
  <li><i class="fas fa-plug"></i> Emacs integration</li>
</ul>
```

### Option B: Two Columns (for wider cards)
```html
<div class="module-features-grid">
  <ul>
    <li>AI-powered</li>
    <li>Intelligent</li>
  </ul>
  <ul>
    <li>Research focused</li>
    <li>Emacs native</li>
  </ul>
</div>
```

## Responsive Considerations

```css
@media (max-width: 768px) {
  .module-features {
    font-size: 0.9rem;
  }
  
  .module-features li {
    margin-bottom: 0.375rem;
  }
}
```

## Testing Checklist

- [ ] Verify alignment on desktop
- [ ] Check mobile responsiveness
- [ ] Test with long feature descriptions
- [ ] Ensure consistent card heights
- [ ] Verify GitHub button positioning
- [ ] Test in dark mode

## Conclusion

This simple change will significantly improve the visual hierarchy and readability of the module cards, making it easier for users to quickly understand what each module offers.
