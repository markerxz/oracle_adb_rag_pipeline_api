import json
import httpx
import re
from typing import List, Tuple

async def semantic_chunk_text(text: str, api_key: str) -> List[Tuple[int, str]]:
    url = "https://api.opentyphoon.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # We enforce JSON output formatting via system prompt to get a structured array of strings.
    system_prompt = (
        "You are an expert document processing assistant. Your task is to perform semantic chunking on the provided text. "
        "The text is extracted via OCR and may contain tables, lists, and paragraphs. "
        "Split the text into logical, semantically meaningful chunks. Keep related context (like a table and its description) together. "
        "Each chunk should be a standalone piece of information, roughly 300 to 800 words, but prioritize semantic completeness over exact word counts. "
        "IMPORTANT: You must return the output EXACTLY as a valid JSON array of strings. Do not include any markdown formatting (like ```json), just the raw JSON array. "
        "Example Output Format: [\"First chunk of text...\", \"Second chunk of text...\", \"Third chunk of text...\"]"
    )

    data = {
        "model": "typhoon-v1.5x-70b-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.1,
        "max_tokens": 8192,
        "top_p": 0.9,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()

# We reverted the changes to the endpoint, I am restoring the file to state before user asked to stop.
