"""Fail if a compose file contains duplicate mapping keys.

YAML resolves a duplicate key by silently keeping the last occurrence. Commit
a6a1107 fixed a merge that had concatenated two versions of
docker-compose.yml, producing exactly that: an ``AUTH_ENABLED: "False"``
appended after ``AUTH_ENABLED: "${AUTH_ENABLED:-True}"``, which reverted the
secure-by-default fix with no conflict marker and no failing test.

PyYAML's default loader accepts duplicates without complaint, so this walks the
node graph directly rather than loading to a dict — by the time you have a
dict, the evidence is gone.
"""

from __future__ import annotations

import sys
from collections import Counter
from typing import Iterator, List, Tuple

import yaml


def _duplicate_keys(node: yaml.Node, path: str = "") -> Iterator[Tuple[str, str, int]]:
    """Yield (path, key, line) for every duplicated mapping key."""
    if isinstance(node, yaml.MappingNode):
        keys = [
            (key_node.value, key_node.start_mark.line + 1)
            for key_node, _ in node.value
            if isinstance(key_node, yaml.ScalarNode)
        ]
        counts = Counter(name for name, _ in keys)
        for name, line in keys:
            if counts[name] > 1:
                yield (path or "<root>", name, line)

        for key_node, value_node in node.value:
            child = key_node.value if isinstance(key_node, yaml.ScalarNode) else "?"
            yield from _duplicate_keys(value_node, f"{path}.{child}" if path else child)

    elif isinstance(node, yaml.SequenceNode):
        for index, item in enumerate(node.value):
            yield from _duplicate_keys(item, f"{path}[{index}]")


def check(path: str) -> List[Tuple[str, str, int]]:
    with open(path, "r", encoding="utf-8") as handle:
        root = yaml.compose(handle)

    if root is None:
        return []
    return list(_duplicate_keys(root))


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("usage: check_compose_duplicate_keys.py <file> [<file>...]", file=sys.stderr)
        return 2

    failed = False
    for path in argv[1:]:
        findings = check(path)
        if findings:
            failed = True
            for where, key, line in findings:
                print(
                    f"{path}:{line}: duplicate key {key!r} in {where} "
                    "— YAML keeps the last occurrence, so the earlier value is "
                    "silently discarded",
                    file=sys.stderr,
                )
        else:
            print(f"{path}: no duplicate keys")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
