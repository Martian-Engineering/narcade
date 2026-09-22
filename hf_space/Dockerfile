FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/data/huggingface \
    NARCADE_RESULTS_DIR=/outputs \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 user \
    && mkdir -p /app /data/huggingface /outputs \
    && chown -R user:user /app /data /outputs

COPY dist/ /tmp/wheels/
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --requirement /tmp/requirements.lock /tmp/wheels/*.whl

COPY --chown=user:user app.py job_runner.py /app/

USER user
WORKDIR /app

EXPOSE 7860
CMD ["python", "/app/app.py"]
