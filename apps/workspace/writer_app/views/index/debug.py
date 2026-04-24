"""Debug views for PDF rendering quality testing."""

from django.http import HttpResponse
from django.views.decorators.cache import never_cache


@never_cache
def test_pdf(request):
    """Generate a test PDF with text at various sizes for quality debugging."""
    html = """<!DOCTYPE html>
<html>
<head>
<style>
  @page { size: letter; margin: 1in; }
  body { font-family: Helvetica, Arial, sans-serif; color: #000; }
  h1 { font-size: 24pt; font-weight: bold; margin-bottom: 0.4in; }
  h2 { font-size: 12pt; font-weight: normal; margin-bottom: 0.6in; color: #333; }
  .size-sample { margin-bottom: 2px; }
  .section-title { font-size: 14pt; font-weight: bold; margin-top: 20px; margin-bottom: 12px; }
  .scientific { margin-bottom: 4px; }
  .code { font-family: Courier, monospace; }
  .serif { font-family: 'Times New Roman', Times, serif; }
  .line-test { margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
  .line { flex: 1; max-width: 5.5in; }
  .line-label { font-size: 8pt; color: #666; }
  .contrast-row { display: flex; gap: 2px; margin-top: 8px; }
  .contrast-box { width: 0.45in; height: 14px; }
</style>
</head>
<body>
  <h1>PDF.js Rendering Quality Test</h1>
  <h2>SciTeX Writer - Debug Page</h2>
"""
    # Various font sizes
    sizes = [6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24]
    for size in sizes:
        html += f'  <div class="size-sample" style="font-size:{size}pt">{size}pt: The quick brown fox jumps over the lazy dog. 0123456789</div>\n'

    # Scientific text samples
    html += '  <div class="section-title">Scientific Text Samples:</div>\n'
    samples = [
        ("serif", 11, "Equation: E = mc\u00b2, \u0394x \u2265 h/4\u03c0"),
        ("", 11, "Statistics: p &lt; 0.001, F(2,47) = 12.34, \u03b7\u00b2 = 0.34"),
        ("code", 10, "Code: def main(): return np.array([1, 2, 3])"),
        ("serif", 10, "Citation: (Smith et al., 2024) reported significant effects."),
        ("", 9, "Table: Mean = 3.45 \u00b1 0.12, N = 150, CI [3.21, 3.69]"),
    ]
    for cls, size, text in samples:
        cls_attr = f' class="scientific {cls}"' if cls else ' class="scientific"'
        html += f'  <div{cls_attr} style="font-size:{size}pt">{text}</div>\n'

    # Sharpness test (thin lines)
    html += '  <div class="section-title">Sharpness Test (thin lines):</div>\n'
    for thickness in [0.25, 0.5, 1.0, 1.5, 2.0]:
        html += f'  <div class="line-test"><div class="line" style="border-top:{thickness}pt solid #000"></div><span class="line-label">{thickness}pt</span></div>\n'

    # Contrast test
    html += '  <div class="section-title">Contrast Test:</div>\n'
    html += '  <div class="contrast-row">\n'
    for i in range(11):
        gray = int(255 * i / 10)
        html += f'    <div class="contrast-box" style="background:rgb({gray},{gray},{gray})"></div>\n'
    html += "  </div>\n"

    html += "</body></html>"

    from weasyprint import HTML

    pdf_bytes = HTML(string=html).write_pdf()
    return HttpResponse(pdf_bytes, content_type="application/pdf")
