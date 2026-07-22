from __future__ import annotations

from pathlib import Path
from typing import Any


class WorkflowConfigError(ValueError):
    pass


def _scalar(value: str) -> object:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[object, int]:
    is_list = lines[index][1].startswith("- ")
    container: object = [] if is_list else {}

    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise WorkflowConfigError(f"unexpected indentation near: {text}")

        if is_list:
            if not text.startswith("- "):
                raise WorkflowConfigError(f"mixed list and mapping near: {text}")
            assert isinstance(container, list)
            container.append(_scalar(text[2:]))
            index += 1
            continue

        if text.startswith("- ") or ":" not in text:
            raise WorkflowConfigError(f"invalid mapping entry: {text}")
        key, raw_value = text.split(":", 1)
        key = key.strip()
        if not key:
            raise WorkflowConfigError("empty mapping key")
        assert isinstance(container, dict)
        index += 1
        if raw_value.strip():
            container[key] = _scalar(raw_value)
            continue
        if index >= len(lines) or lines[index][0] <= current_indent:
            container[key] = {}
            continue
        child, index = _parse_block(lines, index, current_indent + 2)
        container[key] = child

    return container, index


def load_workflow(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise WorkflowConfigError(f"workflow config not found: {path}")

    parsed_lines: list[tuple[int, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if "\t" in raw_line:
            raise WorkflowConfigError("tabs are not supported in workflow config")
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2:
            raise WorkflowConfigError(f"indentation must use two spaces: {stripped}")
        parsed_lines.append((indent, stripped))

    if not parsed_lines:
        raise WorkflowConfigError("workflow config is empty")
    result, consumed = _parse_block(parsed_lines, 0, parsed_lines[0][0])
    if consumed != len(parsed_lines) or not isinstance(result, dict):
        raise WorkflowConfigError("workflow config root must be a mapping")
    return result


def require_string(config: dict[str, Any], dotted_key: str) -> str:
    current: object = config
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise WorkflowConfigError(f"missing required string: {dotted_key}")
        current = current[part]
    if not isinstance(current, str) or not current.strip():
        raise WorkflowConfigError(f"missing required string: {dotted_key}")
    return current
