FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment variables (Defaults, should be overridden in Railway)
ENV DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/shopping_db
ENV SECRET_KEY=your-secret-key-here

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
