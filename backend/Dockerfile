FROM python:3.14-slim

# Debug env vars
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONASYNCIODEBUG=1

WORKDIR /server

COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

EXPOSE 8000

CMD ["sh", "/server/run.sh"]
