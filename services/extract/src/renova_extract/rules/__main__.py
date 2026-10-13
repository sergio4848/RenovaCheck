"""python -m renova_extract.rules {schema|lock} [--write]

``schema`` regenerates packages/rules/schema/rule.schema.json from the model; ``lock`` adds the
hashes of new rule versions to packages/rules/rules.lock.json. Without ``--write`` both only check.
A changed hash of an already published version is never rewritten: publish a new version instead.
"""

from __future__ import annotations

import argparse
import json
import sys

from renova_extract.core.config import Settings
from renova_extract.rules.loader import load_rules, lock_entries, lock_path, rule_schema, schema_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="renova_extract.rules")
    parser.add_argument("task", choices=["schema", "lock"])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    root = Settings().rules_dir

    if args.task == "schema":
        text = json.dumps(rule_schema(), indent=2, ensure_ascii=False) + "\n"
        path = schema_path(root)
        if args.write:
            path.write_text(text)
            return 0
        return 0 if path.exists() and path.read_text() == text else 1

    path = lock_path(root)
    published: dict[str, str] = json.loads(path.read_text()) if path.exists() else {}
    current = lock_entries(load_rules(root))
    changed = sorted(k for k, h in current.items() if k in published and published[k] != h)
    removed = sorted(set(published) - set(current))
    for key in changed:
        print(f"{key}: content changed; publish it as a new version", file=sys.stderr)  # noqa: T201
    for key in removed:
        print(f"{key}: published version is missing", file=sys.stderr)  # noqa: T201
    if changed or removed:
        return 1
    if args.write:
        path.write_text(json.dumps({**published, **current}, indent=2, sort_keys=True) + "\n")
        return 0
    return 0 if set(current) == set(published) else 1


if __name__ == "__main__":
    sys.exit(main())
