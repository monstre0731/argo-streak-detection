FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/ pipeline/

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

# The Argo templates set command: [python, -m, pipeline] explicitly (the emissary executor
# needs it for images that are not in a registry) and pass the step as args.
ENTRYPOINT ["python", "-m", "pipeline"]
