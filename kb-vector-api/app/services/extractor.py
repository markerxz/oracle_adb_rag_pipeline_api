import fitz
import io

def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Processes a PDF byte stream into raw text using PyMuPDF.
    """
    doc = fitz.open(stream=file_content, filetype="pdf")
    pdf_text = ""
    for page in doc:
        pdf_text += page.get_text("text") + "\n"
    return pdf_text
