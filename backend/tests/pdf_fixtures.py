import io

from reportlab.pdfgen import canvas


def make_test_pdf_bytes(page_count: int = 1, text: str = None) -> bytes:
    """Generate a valid PDF with optionally extractable page text."""
    buf = io.BytesIO()

    pdf = canvas.Canvas(buf, pagesize=(100, 100))

    for _ in range(page_count):
        if text:
            pdf.drawString(10, 50, text)

        pdf.showPage()

    pdf.save()

    return buf.getvalue()