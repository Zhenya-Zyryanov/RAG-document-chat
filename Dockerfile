FROM node:lts AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m nltk.downloader snowball_data punkt punkt_tab

COPY backend/ ./backend/
COPY app/ ./app/

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-base')"
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000

ENV QDRANT_HOST=qdrant
ENV QDRANT_PORT=6333
ENV LLM_API_KEY=sk-bhvXTbqF959YWxmxTFnbMA
ENV LLM_BASE_URL=https://litellm.happyhub.ovh/v1
ENV MODEL_NAME=gpt-oss-120b

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]