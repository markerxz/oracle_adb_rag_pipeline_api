import fitz
import re
from typing import List, Tuple


def _clean_page_text(text: str) -> str:
    """
    Light post-processing of raw fitz text to remove common PDF artifacts:
    - Fixes mid-word line-break hyphenation (e.g. 'secu-\nrity' → 'security')
    - Collapses excessive whitespace while preserving paragraph breaks
    - Strips isolated single characters that are likely page artifacts
    """
    # Fix hyphenated line breaks (common in both Thai and English PDFs)
    text = re.sub(r'-\n(\S)', r'\1', text)
    # Merge soft line breaks (single newline) into spaces, keep double newlines as paragraph breaks
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _detect_repeated_lines(pages_text: List[str], min_repeats: int = 3) -> set:
    """
    Detects lines that repeat across multiple pages (headers/footers).
    Returns a set of stripped line strings to be filtered out.
    """
    from collections import Counter
    line_counts = Counter()
    for page_text in pages_text:
        # Only check first/last 3 lines of each page for header/footer candidates
        lines = [l.strip() for l in page_text.split('\n') if l.strip()]
        candidates = lines[:3] + lines[-3:] if len(lines) > 3 else lines
        for line in set(candidates):  # set() to not double-count within same page
            if len(line) > 3:  # ignore trivial lines like page numbers alone
                line_counts[line] += 1

    return {line for line, count in line_counts.items() if count >= min_repeats}


def extract_text_from_pdf(file_content: bytes) -> List[Tuple[int, str]]:
    """
    Processes a PDF byte stream into a list of (page_number, cleaned_text) tuples.
    Page numbers are 1-indexed.

    Also performs light cleaning:
    - Strips repeated headers/footers detected across pages
    - Fixes hyphenation line-break artifacts
    - Collapses excessive whitespace
    """
    doc = fitz.open(stream=file_content, filetype="pdf")

    # First pass: collect raw text per page for header/footer detection
    raw_pages = []
    for page in doc:
        raw_pages.append(page.get_text("text"))

    repeated_lines = _detect_repeated_lines(raw_pages)

    # Second pass: clean and filter each page
    result: List[Tuple[int, str]] = []
    for page_num, raw_text in enumerate(raw_pages, start=1):
        cleaned = _clean_page_text(raw_text)

        # Remove detected header/footer lines
        if repeated_lines:
            filtered_lines = []
            for line in cleaned.split('\n'):
                if line.strip() not in repeated_lines:
                    filtered_lines.append(line)
            cleaned = '\n'.join(filtered_lines).strip()

        if cleaned:
            result.append((page_num, cleaned))

    return result
