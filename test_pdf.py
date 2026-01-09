from fpdf import FPDF

def create_pdf_from_text(text: str, title: str = "Extracted Content") -> bytes:
    """Creates a simple PDF from text string and returns bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    
    # Handle encoding
    safe_text = text.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.multi_cell(0, 10, safe_text)
    
    # Return bytes
    # For FPDF (original), output(dest='S') returns a string (latin-1 string actually).
    # We need to ensure we return bytes.
    return pdf.output(dest='S').encode('latin-1')

try:
    pdf_bytes = create_pdf_from_text("This is a test schedule.", "Test Project")
    print(f"PDF Size: {len(pdf_bytes)} bytes")
    with open("test_output.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("PDF successfully written.")
except Exception as e:
    print(f"Error: {e}")
