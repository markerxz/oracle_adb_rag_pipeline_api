FROM python:3.9-slim

WORKDIR /app

# Install system basics
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Preload the 86MB Sentence Transformer model during build
RUN pip install --no-cache-dir -r requirements.txt && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy Project
COPY ./app /app/app
COPY ./init_db.py /app/
COPY ./README.md /app/

# Expose FastAPI Port
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
