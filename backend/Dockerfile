FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

WORKDIR /app/backend
COPY . .

WORKDIR /app
EXPOSE 8003

ENV PYTHONPATH=/app
ENV USE_STANDALONE=false

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8003"]
