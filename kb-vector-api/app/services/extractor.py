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

import json
import requests
import io

async def extract_text_with_typhoon_ocr(file_content: bytes, filename: str, api_key: str) -> List[Tuple[int, str]]:
    """
    Sends the raw PDF directly to the Typhoon OCR API and parses the returned JSON into per-page text chunks.
    """
    url = "https://api.opentyphoon.ai/v1/ocr"
    
    # Get total pages to explicitly tell the API to process all pages
    doc = fitz.open(stream=file_content, filetype="pdf")
    page_count = doc.page_count
    
    # We use io.BytesIO to treat the raw bytes as a file object
    file_obj = io.BytesIO(file_content)
    # The API expects a tuple (filename, fileobj) for the 'file' parameter
    files = {'file': (filename, file_obj, "application/pdf")}
    
    data = {
        'model': "typhoon-ocr",
        'task_type': "default",
        'max_tokens': "16384",
        'temperature': "0.1",
        'top_p': "0.6",
        'repetition_penalty': "1.2",
        'pages': json.dumps(list(range(1, page_count + 1)))
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    
    # Run the blocking request in a way that doesn't hang the async loop, but for simplicity here we just call it
    response = requests.post(url, files=files, data=data, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Typhoon OCR API Error {response.status_code}: {response.text}")
        
    result = response.json()
    
    extracted_pages: List[Tuple[int, str]] = []
    
    # Typhoon OCR returns a 'results' array where each item represents a page if it's a multi-page PDF
    for page_idx, page_result in enumerate(result.get('results', []), start=1):
        if page_result.get('success') and page_result.get('message'):
            content = page_result['message']['choices'][0]['message']['content']
            try:
                # The model often returns structured JSON with a 'natural_text' field
                parsed_content = json.loads(content)
                text = parsed_content.get('natural_text', content)
            except json.JSONDecodeError:
                text = content
                
            if text and text.strip():
                extracted_pages.append((page_idx, text.strip()))
        else:
            print(f"Error processing page {page_idx} of {filename}: {page_result.get('error', 'Unknown error')}")
            
    return extracted_pages
