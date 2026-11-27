# OWNER: Person 1. Container for Render (or any Docker host; they set PORT).
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=7860
CMD uvicorn server:app --host 0.0.0.0 --port $PORT
