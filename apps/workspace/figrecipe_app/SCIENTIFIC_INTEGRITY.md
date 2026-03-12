# Scientific Integrity in SciTeX Vis

## Core Principle

**SciTeX Vis prioritizes scientific integrity while providing powerful editing tools.**

Unlike general-purpose image editors, SciTeX Vis is designed with research ethics in mind, preventing accidental data manipulation while enabling legitimate figure preparation.

---

## Design Philosophy

### 1. Non-Destructive Editing

**Principle**: Original data is NEVER modified.

```
Original Image (PNG from scitex.plt)
    ↓ Always preserved
    ↓
Canvas Overlay Layer
    ├─ Annotations (text, arrows, ***)
    ├─ Scale bars
    ├─ Panel labels (A, B, C, D)
    └─ White/black rectangles (masking)
    ↓
Exported Figure
    ✓ Original + Overlays
    ✓ Metadata preserved
    ✓ All operations documented
```

**Implementation**:
- Base images loaded as locked objects
- All annotations are overlay layers
- Original files retained in database
- Export includes metadata JSON

---

## Allowed Operations

### Safe Operations (✅ No Warnings)

**These operations do NOT alter underlying data:**

1. **Geometric Transformations**
   - Rotation (90°, 180°, 270°)
   - Flipping (horizontal/vertical)
   - Cropping
   - **Why safe**: No data values changed

2. **Overlay Annotations**
   - Text labels
   - Arrows and lines
   - Statistical markers (***)
   - Scale bars
   - Shapes (rectangles, circles)
   - **Why safe**: Non-destructive overlays

3. **Panel Arrangement**
   - Layout changes (2×2, 1×3, etc.)
   - A/B/C/D labels
   - Alignment and distribution
   - **Why safe**: Compositional only

4. **Masking (White/Black Rectangles)**
   - Hide author information
   - Hide noisy regions
   - Hide irrelevant elements
   - **Why acceptable**: Documented, non-destructive overlay
   - **Requirement**: Must be disclosed in figure legend

### Current Implementation

```typescript
// White Rectangle - Common use case
private addRectangle(fillColor: string, description: string) {
    // SCIENTIFIC INTEGRITY NOTE:
    // White rectangles are commonly used to hide author info, noise, or
    // irrelevant elements. This is acceptable practice when disclosed.
    // The operation is non-destructive (overlays, doesn't modify original).

    const rect = new fabric.Rect({
        fill: fillColor,
        // Light border for visibility
        stroke: fillColor === '#ffffff' ? '#cccccc' : 'none',
        strokeDashArray: fillColor === '#ffffff' ? [3, 3] : [],
    });

    // Add to canvas as overlay
    canvas.add(rect);
}
```

---

## Operations Requiring Documentation (⚠️ Yellow Tier)

**Future implementation - not in current MVP**

These operations are scientifically acceptable BUT require disclosure:

1. **Linear Brightness/Contrast**
   - **Allowed**: Global, linear adjustments only
   - **Not allowed**: Selective, non-linear
   - **Requirement**: Document in figure legend
   - **Example**: "Brightness increased by 20% globally for clarity"

2. **Downsampling/Resize**
   - **Allowed**: Reducing resolution only
   - **Not allowed**: Upscaling (creates artificial detail)
   - **Requirement**: State original resolution

3. **Colormap Changes**
   - **Allowed**: Grayscale ↔ Color, colorblind-safe palettes
   - **Requirement**: State which colormap used
   - **Example**: "Heatmap shown using Viridis colormap for colorblind accessibility"

### Future Implementation (Phase 2)

```typescript
function adjustBrightness(value: number) {
    // Validation
    if (value < -50 || value > 50) {
        throw new Error('Adjustment limited to ±50%');
    }

    // Show documentation requirement
    const legendText = `Brightness adjusted by ${value}% globally for visualization clarity. Original image preserved.`;

    const confirmed = showWarning({
        title: 'Image Adjustment',
        message: `
            ⚠️ This operation must be documented

            Required figure legend text:
            "${legendText}"

            Continue?
        `
    });

    if (!confirmed) return;

    // Apply linear transformation
    applyLinearBrightness(value);

    // Save metadata
    metadata.operations.push({
        type: 'brightness',
        value: value,
        suggestedLegend: legendText
    });
}
```

---

## Prohibited Operations (⛔ Red Tier)

**These will be BLOCKED with educational explanations:**

1. **Selective Editing**
   - Adjusting only part of an image
   - **Why prohibited**: Can selectively enhance/suppress features
   - **Violates**: NIH, NSF, journal policies

2. **Non-Linear Enhancements**
   - Gamma correction
   - Histogram equalization
   - **Why prohibited**: Alters data relationships

3. **Content-Aware Fill**
   - Adding non-existent content
   - **Why prohibited**: Data fabrication

4. **AI Enhancement**
   - Super-resolution
   - Denoising with AI
   - **Why prohibited**: May introduce artifacts

### Educational Approach

```typescript
function attemptProhibitedOperation(operation: string) {
    showError({
        title: 'Operation Not Allowed',
        message: `
            ⛔ ${operation} is not permitted in SciTeX Vis

            Reason:
            This operation may constitute research misconduct
            according to:
            - Office of Research Integrity (ORI)
            - Nature Publishing Group guidelines
            - Science Magazine policies

            Consequences:
            - Paper rejection
            - Retraction
            - Loss of credibility

            Instead, consider:
            ✓ Re-acquiring the image with better parameters
            ✓ Presenting original data with appropriate labeling
            ✓ Using accepted annotation methods

            Learn more:
            [Link to ORI guidelines]
            [Link to journal policies]
        `,
        severity: 'critical'
    });
}
```

---

## Metadata & Documentation

### Automatic Documentation

Every operation is recorded:

```json
{
  "figure_id": "uuid",
  "original_image": "experiment1.png",
  "operations": [
    {
      "type": "annotation",
      "tool": "white_rectangle",
      "timestamp": "2025-11-15T23:00:00Z",
      "position": {"x": 100, "y": 50},
      "size": {"w": 150, "h": 100},
      "purpose": "hide_author_info",
      "disclosure": "Required: Must mention in figure legend"
    },
    {
      "type": "annotation",
      "tool": "scale_bar",
      "length_um": 100,
      "calibration": "10px_per_um"
    }
  ],
  "suggested_legend": "Author information obscured with white rectangle. Scale bar: 100 μm."
}
```

### Export Behavior

When exporting, SciTeX Vis will:

1. **Export the figure** (PNG/SVG)
2. **Export metadata** (JSON with all operations)
3. **Generate suggested legend text**
4. **Copy legend to clipboard** (optional)
5. **Warn if disclosure needed**

```
Export complete!

✅ Figure: figure_final.png
✅ Metadata: figure_metadata.json
✅ Original: experiment1_original.png (preserved)

⚠️ DISCLOSURE REQUIRED:
Your figure legend should include:
"Author information obscured for anonymity. Original unmodified image available upon request."

[Copy to Clipboard] [Continue]
```

---

## Comparison with Other Tools

| Tool | Approach | Scientific Integrity |
|------|----------|---------------------|
| **Adobe Illustrator** | Allows everything | ❌ No safeguards |
| **Photoshop** | Allows everything | ❌ No safeguards |
| **ImageJ/Fiji** | Some warnings | ⚠️ Limited guidance |
| **SciTeX Vis** | **Three-tier system** | ✅ **Built-in ethics** |

### SciTeX Vis Advantage

1. **Prevents accidents** - Blocks dangerous operations
2. **Educates users** - Explains why operations are problematic
3. **Enforces documentation** - Requires disclosure
4. **Maintains provenance** - Complete operation history
5. **Follows standards** - Aligned with ORI, Nature, Science

---

## Journal Guidelines Compliance

### Nature Publishing Group

> "No specific feature within an image may be enhanced, obscured, moved, removed or introduced."

**SciTeX Vis Compliance**:
- ✅ Annotations allowed (labels, arrows, text)
- ✅ White rectangles for masking (if disclosed)
- ❌ Brightness/contrast blocked or requires documentation
- ❌ Selective editing blocked

### Science Magazine

> "Images should not be manipulated in any way that could mislead reviewers or readers."

**SciTeX Vis Compliance**:
- ✅ All operations logged and disclosed
- ✅ Original images preserved
- ❌ Misleading enhancements blocked

### Office of Research Integrity (ORI)

> "Digital images should not be manipulated or enhanced in any way that could affect interpretation of the data."

**SciTeX Vis Compliance**:
- ✅ Three-tier system prevents violations
- ✅ Educational approach
- ✅ Complete transparency

---

## User Guidance

### When Creating Figures

**Do:**
- ✅ Add text labels, arrows, scale bars
- ✅ Create panel layouts (A, B, C, D)
- ✅ Use white rectangles to hide non-data elements (with disclosure)
- ✅ Crop to relevant regions
- ✅ Export with metadata

**Don't:**
- ❌ Adjust brightness of specific regions
- ❌ Remove or add features selectively
- ❌ Use AI enhancement tools
- ❌ Modify data values

**If Unsure:**
- Consult your institution's research integrity office
- Check journal-specific guidelines
- When in doubt, don't modify - annotate instead

---

## Future Enhancements (Phase 2)

### Planned Features with Scientific Integrity

1. **Colorblind-Safe Palette Checker**
   - Analyze figure colors
   - Suggest accessible alternatives
   - **Safe**: Doesn't alter data, improves accessibility

2. **Figure Quality Checker**
   - Check resolution (≥300 DPI?)
   - Check font sizes (≥6pt?)
   - Check for common issues
   - **Safe**: Advisory only, no modifications

3. **Auto-Documentation Generator**
   - Scan all operations
   - Generate Methods section text
   - Generate Figure legend text
   - **Helpful**: Ensures complete disclosure

4. **Comparison Mode**
   - Show original vs edited side-by-side
   - Highlight differences
   - **Transparent**: Makes modifications visible

---

## Conclusion

**SciTeX Vis is the first scientific figure editor with ethics built-in.**

By design, it:
- Makes the right thing easy
- Makes the wrong thing hard (or impossible)
- Educates researchers
- Enforces transparency
- Prevents career-ending mistakes

This is not just a tool - it's a **guardian of scientific integrity**. 🛡️

---

## References

- [Office of Research Integrity - Image Guidelines](https://ori.hhs.gov/)
- [Nature - Image Integrity](https://www.nature.com/nature-portfolio/editorial-policies/image-integrity)
- [Science - Image Guidelines](https://www.science.org/content/page/science-journals-editorial-policies)
- [NIH Guidelines for Scientific Integrity](https://www.nih.gov/)

---

<!-- EOF -->
