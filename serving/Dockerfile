# Multi-stage: the builder trains the model, the runtime serves it lean.
# Build from the project ROOT:  docker build -t churnml-serving -f serving/Dockerfile .

# --- Stage 1: builder ------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    VENV=/opt/venv

RUN python -m venv $VENV
ENV PATH="$VENV/bin:$PATH"

WORKDIR /build

# Service runtime dependencies (layer caching).
COPY serving/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Package code + data/training pipeline -> install and train the model.
COPY pyproject.toml params.yaml ./
COPY src ./src
COPY scripts ./scripts
# Non-editable install (--no-deps): churnml goes into site-packages,
# so it survives copying the venv into the runtime (model.joblib references
# churnml.features.engineer when unpickling).
RUN pip install --no-deps .

# We run training from the source tree (PYTHONPATH=src) so that the
# params.yaml / data / model.joblib paths resolve relative to /build.
RUN PYTHONPATH=/build/src python scripts/make_data.py \
    && PYTHONPATH=/build/src python -m churnml.prepare \
    && PYTHONPATH=/build/src python -m churnml.train

# --- Stage 2: runtime ------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /srv

# Environment (with churnml installed) + trained model + service code.
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/model.joblib /srv/model.joblib
COPY serving ./serving

EXPOSE 17100

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:17100/health').status==200 else 1)"

CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "17100"]
