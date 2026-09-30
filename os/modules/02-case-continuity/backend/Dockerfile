FROM python:3.12-slim

WORKDIR /srv/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY frontend/ /srv/frontend

RUN mkdir -p /data/uploads

EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
