# syntax=docker/dockerfile:1.7
# Synthetic document generator. Writes to /work/data (bind mount); reads the schema from
# /work/packages/rules (read-only bind mount).
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bookworm
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    RENOVA_SCHEMA_PATH=/work/packages/rules/schema/ground_truth.schema.json
COPY --from=certs . /usr/local/share/ca-certificates/extra/
RUN update-ca-certificates >/dev/null 2>&1 || true
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
RUN pip install ".[dev]"
WORKDIR /work
ENTRYPOINT ["renova-synth"]
CMD ["generate", "--out", "/work/data/synth", "--cases", "20", "--seed", "2026"]
