FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py start.py ./
COPY redact ./redact
COPY data ./data
COPY templates ./templates
COPY static ./static
COPY samples/ticket_log.txt ./samples/ticket_log.txt

EXPOSE 8000

CMD ["python", "start.py"]
