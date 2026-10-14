"""Container healthcheck: exit 0 while the worker heartbeat is fresh."""

from __future__ import annotations

import sys
import time

from renova_extract.worker.runner import HEARTBEAT_FILE

MAX_AGE_SECONDS = 60


def main() -> int:
    try:
        beat = int(HEARTBEAT_FILE.read_text())
    except (OSError, ValueError):
        return 1
    return 0 if time.time() - beat <= MAX_AGE_SECONDS else 1


if __name__ == "__main__":
    sys.exit(main())
