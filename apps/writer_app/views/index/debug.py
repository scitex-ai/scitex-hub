"""Debug views for PDF rendering quality testing."""

import io

from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


@never_cache
def test_pdf(request):
    """Generate a test PDF with text at various sizes for quality debugging."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1 * inch, h - 1 * inch, "PDF.js Rendering Quality Test")

    # Subtitle
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, h - 1.4 * inch, "SciTeX Writer - Debug Page")

    # Various font sizes
    y = h - 2 * inch
    sizes = [6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24]
    for size in sizes:
        c.setFont("Helvetica", size)
        c.drawString(
            1 * inch,
            y,
            f"{size}pt: The quick brown fox jumps over the lazy dog. 0123456789",
        )
        y -= size * 1.5

    # Math-like content
    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, y, "Scientific Text Samples:")
    y -= 24

    samples = [
        ("Times-Roman", 11, "Equation: E = mc\u00b2, \u0394x \u2265 h/4\u03c0"),
        (
            "Helvetica",
            11,
            "Statistics: p < 0.001, F(2,47) = 12.34, \u03b7\u00b2 = 0.34",
        ),
        ("Courier", 10, "Code: def main(): return np.array([1, 2, 3])"),
        (
            "Times-Roman",
            10,
            "Citation: (Smith et al., 2024) reported significant effects.",
        ),
        ("Helvetica", 9, "Table: Mean = 3.45 \u00b1 0.12, N = 150, CI [3.21, 3.69]"),
    ]
    for font, size, text in samples:
        c.setFont(font, size)
        c.drawString(1 * inch, y, text)
        y -= size * 1.8

    # Fine lines for sharpness testing
    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, y, "Sharpness Test (thin lines):")
    y -= 20
    for thickness in [0.25, 0.5, 1.0, 1.5, 2.0]:
        c.setLineWidth(thickness)
        c.line(1 * inch, y, 6.5 * inch, y)
        c.setFont("Helvetica", 8)
        c.drawString(6.7 * inch, y - 3, f"{thickness}pt")
        y -= 12

    # Gray gradient for contrast testing
    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, y, "Contrast Test:")
    y -= 16
    for i in range(11):
        gray = i / 10.0
        c.setFillGray(gray)
        c.rect(1 * inch + i * 0.5 * inch, y, 0.45 * inch, 14, fill=1)
    c.setFillGray(0)

    c.showPage()
    c.save()
    buf.seek(0)
    return HttpResponse(buf.read(), content_type="application/pdf")
