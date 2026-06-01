"""Reader and annotation helpers for comprehension capture files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterator, TextIO

from forge_bridge.comprehension._schema import (
    SCHEMA_VERSION,
    SchemaValidationError,
    SchemaVersionMismatch,
    VERDICT_VALUES,
    validate_comprehension_record,
)


def _parse_json_line(raw: str, *, path: Path, lineno: int) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(
            f"{path}:{lineno}: malformed JSON: {exc.msg}"
        ) from exc
    if not isinstance(parsed, dict):
        raise SchemaValidationError(f"{path}:{lineno}: line must be a JSON object")
    return parsed


def _check_header(header: dict, *, path: Path) -> None:
    if header.get("_header") is not True:
        raise SchemaVersionMismatch(
            f"comprehension file {path} has no header record; "
            f"reader expects schema_version={SCHEMA_VERSION!r}."
        )
    version = header.get("schema_version")
    if version != SCHEMA_VERSION:
        raise SchemaVersionMismatch(
            f"schema_version={version} records require reader version "
            f"{SCHEMA_VERSION}; upgrade or filter."
        )


def read_comprehension_file(path: Path) -> Iterator[dict]:
    """Yield validated comprehension records from a JSONL capture file."""
    with path.open("r", encoding="utf-8") as fh:
        header: dict | None = None
        for lineno, raw in enumerate(fh, start=1):
            if raw.strip() == "":
                continue
            header = _parse_json_line(raw, path=path, lineno=lineno)
            _check_header(header, path=path)
            break
        if header is None:
            raise SchemaVersionMismatch(
                f"comprehension file {path} is empty or has no header record; "
                f"reader expects schema_version={SCHEMA_VERSION!r}."
            )

        for lineno, raw in enumerate(fh, start=lineno + 1):
            if raw.strip() == "":
                continue
            record = _parse_json_line(raw, path=path, lineno=lineno)
            validate_comprehension_record(record)
            yield record


def annotate_comprehension_file(
    path: Path,
    *,
    input_func: Callable[[str], str] = input,
    output: TextIO | None = None,
) -> int:
    """Prompt for verdicts on untagged records and rewrite the file.

    Returns the number of records tagged. Already-tagged records are preserved
    and skipped.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise SchemaVersionMismatch(
            f"comprehension file {path} is empty or has no header record; "
            f"reader expects schema_version={SCHEMA_VERSION!r}."
        )

    parsed: list[dict] = []
    header_seen = False
    for index, raw in enumerate(lines, start=1):
        if raw.strip() == "":
            continue
        item = _parse_json_line(raw, path=path, lineno=index)
        if not header_seen:
            _check_header(item, path=path)
            parsed.append(item)
            header_seen = True
            continue
        validate_comprehension_record(item)
        parsed.append(item)

    if not header_seen:
        raise SchemaVersionMismatch(
            f"comprehension file {path} is empty or has no header record; "
            f"reader expects schema_version={SCHEMA_VERSION!r}."
        )

    tagged = 0
    choices = "/".join(sorted(VERDICT_VALUES))
    for record in parsed[1:]:
        if record.get("verdict") is not None:
            continue
        if output is not None:
            print(f"Question: {record['question']}", file=output)
            print(f"Answer: {record['answer']}", file=output)
            print("Chain:", file=output)
            print(json.dumps(record["chain"], indent=2, sort_keys=True), file=output)
        while True:
            verdict = input_func(f"Verdict ({choices}): ").strip()
            if verdict in VERDICT_VALUES:
                record["verdict"] = verdict
                tagged += 1
                break

    payload = "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
        for item in parsed
    )
    path.write_text(payload, encoding="utf-8")
    return tagged
