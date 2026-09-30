FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATABASE_URL=sqlite:////app/data/registry_defect_engine.db
ENV STORAGE_ROOT=/app/data/storage
RUN mkdir -p /app/data/storage

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
