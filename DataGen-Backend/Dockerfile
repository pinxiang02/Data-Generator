# DataGen backend (FastAPI)
FROM python:3.13-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY . .

EXPOSE 8000

# DATABASE_URL is injected by compose to point at the postgres service.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
