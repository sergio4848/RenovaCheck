# renova-extract

Stateless FastAPI service (`renova_extract.api.app:create_app`) and batch worker
(`python -m renova_extract.worker`) for RenovaCheck. Settings come from `RENOVA_*`
environment variables (see `src/renova_extract/core/config.py`).

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest            # unit tests
.venv/bin/ruff check . && .venv/bin/mypy
```
