FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/ pipeline/

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

# Argo passes the subcommand as args, e.g. ["calibrate", "--frame", "frame-003"]
ENTRYPOINT ["python", "-m", "pipeline"]
