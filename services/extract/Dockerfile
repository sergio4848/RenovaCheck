# syntax=docker/dockerfile:1.7
# Adapted from careos/apps/backend/Dockerfile — Copyright (c) 2026 Sergen Şahin.
# One image, two entrypoints: API (uvicorn) and batch worker (python -m renova_extract.worker).
#
#   docker build --build-context certs=../../infra/certs -t renova-extract .   # includes dev/test tooling
#   docker build --build-arg INSTALL_DEV=false -t renova-extract:prod .

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim-bookworm AS build
ARG INSTALL_DEV=true
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
# Optional extra CA certificates for builds behind a TLS-intercepting proxy (see infra/certs/README.md).
COPY --from=certs . /usr/local/share/ca-certificates/extra/
RUN update-ca-certificates >/dev/null 2>&1 || true
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Dependency layer (cached until pyproject.toml changes)
COPY pyproject.toml README.md ./
RUN python - <<'PY'
import os, tomllib
project = tomllib.load(open("pyproject.toml", "rb"))["project"]
deps = list(project["dependencies"])
if os.environ.get("INSTALL_DEV", "true") == "true":
    deps += project["optional-dependencies"]["dev"]
open("/tmp/requirements.txt", "w").write("\n".join(deps) + "\n")
PY
RUN pip install -r /tmp/requirements.txt

COPY src ./src
RUN pip install --no-deps .

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    RENOVA_RULES_DIR=/app/rules
# Local OCR fallback for pages without a text layer (TesseractPol adapter).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-pol \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --system --gid 10001 renova \
    && useradd --system --uid 10001 --gid renova --home-dir /app --shell /usr/sbin/nologin renova
WORKDIR /app
RUN chown renova:renova /app
COPY --from=build /opt/venv /opt/venv
# Source and tests are also shipped so lint and tests run inside the image (make lint/test).
COPY --chown=renova:renova pyproject.toml README.md ./
COPY --chown=renova:renova src ./src
COPY --chown=renova:renova tests ./tests
COPY --from=rules --chown=renova:renova . ./rules
USER renova
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 --start-period=10s \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "renova_extract.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
