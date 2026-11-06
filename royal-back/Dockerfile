FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

COPY royal-back/requirements.txt /app/royal-back/requirements.txt
RUN pip install --no-cache-dir -r /app/royal-back/requirements.txt

COPY royal-back /app/royal-back
COPY royal-front /app/royal-front

RUN mkdir -p /app/royal-back/data/evidencias /tmp/matplotlib

WORKDIR /app/royal-back
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
