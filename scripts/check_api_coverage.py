#!/usr/bin/env python3
"""Coverage gate: verifies every name in pydbc_core.__all__ has a ## <Name> section in docs/api-reference.md.

Exit 0  — all exported names are documented
Exit 1  — one or more names are missing; prints the list
"""
import importlib
import os
import re
import sys


def main() -> int:
    # Locate docs/api-reference.md relative to this script (scripts/ -> project root -> docs/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    doc_path = os.path.join(script_dir, "..", "docs", "api-reference.md")
    doc_path = os.path.normpath(doc_path)

    # Import pydbc_core to read __all__
    try:
        pydbc_core = importlib.import_module("pydbc_core")
    except ModuleNotFoundError as exc:
        print(f"ERROR: could not import pydbc_core — {exc}", file=sys.stderr)
        print("Run via: uv run python scripts/check_api_coverage.py", file=sys.stderr)
        return 2

    exported_names: list[str] = list(pydbc_core.__all__)
    total = len(exported_names)

    # Read the API reference doc
    try:
        with open(doc_path, encoding="utf-8") as fh:
            doc_text = fh.read()
    except FileNotFoundError:
        print(f"ERROR: {doc_path} not found", file=sys.stderr)
        return 2

    # Check each name for a ## <Name> heading (exact match, whole line)
    documented: list[str] = []
    missing: list[str] = []
    for name in exported_names:
        pattern = rf"^## {re.escape(name)}$"
        if re.search(pattern, doc_text, re.MULTILINE):
            documented.append(name)
        else:
            missing.append(name)

    found = len(documented)
    print(f"{found}/{total} exported names documented")

    if missing:
        print("\nMissing sections:")
        for name in missing:
            print(f"  ## {name}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
