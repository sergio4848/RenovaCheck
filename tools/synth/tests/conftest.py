from __future__ import annotations

from pathlib import Path

import pytest

from renova_synth.generate import generate


@pytest.fixture(scope="session")
def dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("synth") / "data"
    generate(root, cases=20, seed=2026)
    return root
