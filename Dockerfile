FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY web /app/web
COPY src /app/src

EXPOSE 8001 8002 8003

CMD ["uvicorn", "ucdc.consent_api:app", "--host", "0.0.0.0", "--port", "8001"]

