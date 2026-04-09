FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONASYNCIODEBUG=1

# Create non-root user with matching host UID/GID
ARG UID=1000
ARG GID=1000
RUN groupadd --gid ${GID} appuser \
    && useradd --uid ${UID} --gid ${GID} --shell /bin/sh --create-home appuser

WORKDIR /backend

# Install system + python deps as root (needs root for apt and site-packages)
COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# Make the workdir and any runtime-writable dirs owned by appuser.
# These match MEDIA_DIR / TEMPFS_DIR / LOGS_DIR from your config.py.
RUN mkdir -p /backend/shared_media /backend/tempfs_storage /backend/logs \
    && chown -R appuser:appuser /backend

# Drop privileges for everything from here on
USER appuser

EXPOSE 8000

CMD ["sh", "/backend/run.sh"]