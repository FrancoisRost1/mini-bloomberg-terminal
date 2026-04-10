FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p data/cache data/raw data/processed outputs
EXPOSE 8501
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
