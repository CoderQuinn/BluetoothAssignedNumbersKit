#!/usr/bin/env python3
"""Generate a compact offline Bluetooth Assigned Numbers catalog."""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_URL = "https://bitbucket.org/bluetooth-SIG/public.git"
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "Sources/BluetoothAssignedNumbersKit/Data/bluetooth_assigned_numbers.json"
)
SOURCE_PATHS = {
    "companies": Path("assigned_numbers/company_identifiers/company_identifiers.yaml"),
    "services": Path("assigned_numbers/uuids/service_uuids.yaml"),
    "characteristics": Path("assigned_numbers/uuids/characteristic_uuids.yaml"),
    "descriptors": Path("assigned_numbers/uuids/descriptors.yaml"),
    "appearances": Path("assigned_numbers/core/appearance_values.yaml"),
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--snapshot-date")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def scalar(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, str):
                return parsed
        except (SyntaxError, ValueError):
            return value[1:-1]
    return value


def hex_key(raw: str, width: int = 4) -> str:
    return f"{int(raw, 16):0{width}X}"


def parse_companies(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        value_match = re.match(r"^\s*-\s+value:\s*(0x[0-9A-Fa-f]+)\s*$", line)
        if value_match:
            current = hex_key(value_match.group(1))
            continue
        name_match = re.match(r"^\s+name:\s*(.+?)\s*$", line)
        if name_match and current:
            name = scalar(name_match.group(1))
            if name:
                entries[current] = name
            current = None
    return dict(sorted(entries.items()))


def parse_uuid_entries(text: str) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None

    def flush() -> None:
        nonlocal current
        if current and current.get("uuid") and current.get("name"):
            key = current["uuid"]
            entries[key] = current
        current = None

    for line in text.splitlines():
        uuid_match = re.match(r"^\s*-\s+uuid:\s*(0x[0-9A-Fa-f]+)\s*$", line)
        if uuid_match:
            flush()
            key = hex_key(uuid_match.group(1))
            current = {"uuid": key}
            continue
        if current is None:
            continue
        field_match = re.match(r"^\s+(name|id):\s*(.+?)\s*$", line)
        if field_match:
            field = "identifier" if field_match.group(1) == "id" else "name"
            current[field] = scalar(field_match.group(2))
    flush()
    return dict(sorted(entries.items()))


def parse_appearances(text: str) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    category_value: int | None = None
    category_name: str | None = None
    subcategory_value: int | None = None
    subcategory_name: str | None = None

    def flush_subcategory() -> None:
        nonlocal subcategory_value, subcategory_name
        if (
            category_value is not None
            and category_name
            and subcategory_value is not None
            and subcategory_name
        ):
            full_value = (category_value << 6) | subcategory_value
            entries[f"{full_value:04X}"] = {
                "value": full_value,
                "category": category_name,
                "subcategory": subcategory_name,
            }
        subcategory_value = None
        subcategory_name = None

    def flush_category() -> None:
        flush_subcategory()
        if category_value is not None and category_name:
            full_value = category_value << 6
            entries[f"{full_value:04X}"] = {
                "value": full_value,
                "category": category_name,
                "subcategory": None,
            }

    for line in text.splitlines():
        category_match = re.match(r"^\s*-\s+category:\s*(0x[0-9A-Fa-f]+)\s*$", line)
        if category_match:
            flush_category()
            category_value = int(category_match.group(1), 16)
            category_name = None
            continue
        subcategory_match = re.match(r"^\s+-\s+value:\s*(0x[0-9A-Fa-f]+)\s*$", line)
        if subcategory_match and category_value is not None:
            flush_subcategory()
            subcategory_value = int(subcategory_match.group(1), 16)
            continue
        name_match = re.match(r"^\s+name:\s*(.+?)\s*$", line)
        if name_match and category_value is not None:
            name = scalar(name_match.group(1))
            if subcategory_value is None:
                category_name = name
            else:
                subcategory_name = name
    flush_category()
    return dict(sorted(entries.items()))


def source_commit(source_repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source_repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def read_existing(output: Path) -> dict[str, Any] | None:
    if not output.exists():
        return None
    return json.loads(output.read_text(encoding="utf-8"))


def semantic_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result.pop("generatedAt", None)
    return result


def build_payload(source_repo: Path, snapshot_date: str) -> dict[str, Any]:
    texts = {
        key: (source_repo / relative).read_text(encoding="utf-8")
        for key, relative in SOURCE_PATHS.items()
    }
    companies = parse_companies(texts["companies"])
    services = parse_uuid_entries(texts["services"])
    characteristics = parse_uuid_entries(texts["characteristics"])
    descriptors = parse_uuid_entries(texts["descriptors"])
    appearances = parse_appearances(texts["appearances"])

    minimums = {
        "companyIdentifiers": (companies, 3_000),
        "services": (services, 50),
        "characteristics": (characteristics, 200),
        "descriptors": (descriptors, 10),
        "appearances": (appearances, 100),
    }
    for label, (entries, minimum) in minimums.items():
        if len(entries) < minimum:
            raise ValueError(f"{label}: expected at least {minimum}, got {len(entries)}")

    return {
        "schemaVersion": 1,
        "generatedAt": snapshot_date,
        "source": {
            "repository": REPOSITORY_URL,
            "commit": source_commit(source_repo),
        },
        "counts": {
            "companyIdentifiers": len(companies),
            "services": len(services),
            "characteristics": len(characteristics),
            "descriptors": len(descriptors),
            "appearances": len(appearances),
        },
        "companyIdentifiers": companies,
        "services": services,
        "characteristics": characteristics,
        "descriptors": descriptors,
        "appearances": appearances,
    }


def update_catalog(
    source_repo: Path,
    output: Path,
    snapshot_date: str,
    *,
    check: bool,
) -> tuple[bool, str]:
    candidate = build_payload(source_repo, snapshot_date)
    existing = read_existing(output)
    if existing and semantic_payload(existing) == semantic_payload(candidate):
        return False, "up to date"
    if check:
        return True, "update needed"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    counts = candidate["counts"]
    return True, "wrote " + ", ".join(f"{key}={value}" for key, value in counts.items())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    snapshot_date = args.snapshot_date or datetime.now(timezone.utc).date().isoformat()
    try:
        changed, message = update_catalog(
            args.source_repo.resolve(),
            args.output.resolve(),
            snapshot_date,
            check=args.check,
        )
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(message)
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
