#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path


CDC_ID_RE = re.compile(r"^CDC-\d{3}$")
PATH_ID_RE = re.compile(r"^PATH-\d{3}$")


class ValidationError(Exception):
    pass


def load_json_like_yaml(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path} is not valid JSON-compatible YAML: {exc}") from exc


def require_keys(obj: dict, keys: list[str], context: str) -> None:
    for key in keys:
        if key not in obj:
            raise ValidationError(f"{context} is missing required key: {key}")


def require_type(value, expected_type, context: str) -> None:
    if not isinstance(value, expected_type):
        raise ValidationError(f"{context} has wrong type: expected {expected_type.__name__}")


def validate_line_field(value, context: str) -> None:
    if isinstance(value, int):
        return
    if isinstance(value, list) and value and all(isinstance(item, int) for item in value):
        return
    raise ValidationError(f"{context} must be an integer or a non-empty list of integers")


def validate_cdc_report(data: dict) -> None:
    require_type(data, dict, "cdc report")
    require_keys(data, ["module", "file", "clock_domains", "crossings", "summary"], "cdc report")

    require_type(data["module"], str, "cdc report.module")
    require_type(data["file"], str, "cdc report.file")
    require_type(data["clock_domains"], list, "cdc report.clock_domains")
    require_type(data["crossings"], list, "cdc report.crossings")
    require_type(data["summary"], dict, "cdc report.summary")

    for index, item in enumerate(data["clock_domains"], start=1):
        context = f"cdc report.clock_domains[{index}]"
        require_type(item, dict, context)
        require_keys(item, ["name"], context)
        require_type(item["name"], str, f"{context}.name")

    valid_methods = {
        "2ff",
        "3ff",
        "gray",
        "handshake",
        "toggle_snapshot",
        "async_fifo",
        "pulse_sync",
        "none",
    }
    valid_severities = {"critical", "high", "medium", "low", "info"}

    for index, item in enumerate(data["crossings"], start=1):
        context = f"cdc report.crossings[{index}]"
        require_type(item, dict, context)
        require_keys(
            item,
            [
                "id",
                "signal",
                "width",
                "source_domain",
                "dest_domain",
                "line",
                "direction",
                "synchronized",
                "sync_method",
                "severity",
                "description",
            ],
            context,
        )
        if not CDC_ID_RE.match(item["id"]):
            raise ValidationError(f"{context}.id must match CDC-NNN")
        require_type(item["signal"], str, f"{context}.signal")
        require_type(item["width"], int, f"{context}.width")
        require_type(item["source_domain"], str, f"{context}.source_domain")
        require_type(item["dest_domain"], str, f"{context}.dest_domain")
        validate_line_field(item["line"], f"{context}.line")
        require_type(item["direction"], str, f"{context}.direction")
        require_type(item["synchronized"], bool, f"{context}.synchronized")
        if item["sync_method"] not in valid_methods:
            raise ValidationError(f"{context}.sync_method is invalid")
        if item["severity"] not in valid_severities:
            raise ValidationError(f"{context}.severity is invalid")
        require_type(item["description"], str, f"{context}.description")
        if "fix" in item:
            require_type(item["fix"], str, f"{context}.fix")

    summary = data["summary"]
    require_keys(summary, ["total_crossings", "violations", "by_severity"], "cdc report.summary")
    require_type(summary["total_crossings"], int, "cdc report.summary.total_crossings")
    require_type(summary["violations"], int, "cdc report.summary.violations")
    require_type(summary["by_severity"], dict, "cdc report.summary.by_severity")
    require_keys(
        summary["by_severity"],
        ["critical", "high", "medium", "low", "info"],
        "cdc report.summary.by_severity",
    )
    for key, value in summary["by_severity"].items():
        require_type(value, int, f"cdc report.summary.by_severity.{key}")


def validate_timing_report(data: dict) -> None:
    require_type(data, dict, "timing report")
    require_keys(
        data,
        ["module", "file", "config", "registers", "paths", "unresolved", "summary"],
        "timing report",
    )

    require_type(data["module"], str, "timing report.module")
    require_type(data["file"], str, "timing report.file")
    require_type(data["config"], str, "timing report.config")
    require_type(data["registers"], list, "timing report.registers")
    require_type(data["paths"], list, "timing report.paths")
    require_type(data["unresolved"], list, "timing report.unresolved")
    require_type(data["summary"], dict, "timing report.summary")

    valid_sources = {"always_ff", "macro", "library_cell", "inferred"}
    valid_difficulties = {"critical", "hard", "moderate", "easy"}

    for index, item in enumerate(data["registers"], start=1):
        context = f"timing report.registers[{index}]"
        require_type(item, dict, context)
        require_keys(item, ["name", "width", "clock", "source", "line"], context)
        require_type(item["name"], str, f"{context}.name")
        require_type(item["width"], int, f"{context}.width")
        require_type(item["clock"], str, f"{context}.clock")
        if item["source"] not in valid_sources:
            raise ValidationError(f"{context}.source is invalid")
        require_type(item["line"], int, f"{context}.line")

    for index, item in enumerate(data["paths"], start=1):
        context = f"timing report.paths[{index}]"
        require_type(item, dict, context)
        require_keys(
            item,
            ["id", "from", "to", "depth", "difficulty", "stages", "crosses_module", "description"],
            context,
        )
        if not PATH_ID_RE.match(item["id"]):
            raise ValidationError(f"{context}.id must match PATH-NNN")
        require_type(item["from"], str, f"{context}.from")
        require_type(item["to"], str, f"{context}.to")
        require_type(item["depth"], int, f"{context}.depth")
        if item["difficulty"] not in valid_difficulties:
            raise ValidationError(f"{context}.difficulty is invalid")
        require_type(item["stages"], list, f"{context}.stages")
        require_type(item["crosses_module"], bool, f"{context}.crosses_module")
        require_type(item["description"], str, f"{context}.description")
        if "module_path" in item:
            require_type(item["module_path"], list, f"{context}.module_path")
            if not all(isinstance(part, str) for part in item["module_path"]):
                raise ValidationError(f"{context}.module_path must contain only strings")
        if "suggestion" in item:
            require_type(item["suggestion"], str, f"{context}.suggestion")

        for stage_index, stage in enumerate(item["stages"], start=1):
            stage_context = f"{context}.stages[{stage_index}]"
            require_type(stage, dict, stage_context)
            require_keys(stage, ["op", "width", "depth", "line"], stage_context)
            require_type(stage["op"], str, f"{stage_context}.op")
            require_type(stage["width"], int, f"{stage_context}.width")
            require_type(stage["depth"], int, f"{stage_context}.depth")
            require_type(stage["line"], int, f"{stage_context}.line")

    for index, item in enumerate(data["unresolved"], start=1):
        context = f"timing report.unresolved[{index}]"
        require_type(item, dict, context)
        require_keys(item, ["name", "line", "reason"], context)
        require_type(item["name"], str, f"{context}.name")
        require_type(item["line"], int, f"{context}.line")
        require_type(item["reason"], str, f"{context}.reason")

    summary = data["summary"]
    require_keys(
        summary,
        ["total_registers", "total_paths", "by_difficulty", "deepest_path"],
        "timing report.summary",
    )
    require_type(summary["total_registers"], int, "timing report.summary.total_registers")
    require_type(summary["total_paths"], int, "timing report.summary.total_paths")
    require_type(summary["by_difficulty"], dict, "timing report.summary.by_difficulty")
    require_keys(
        summary["by_difficulty"],
        ["critical", "hard", "moderate", "easy"],
        "timing report.summary.by_difficulty",
    )
    for key, value in summary["by_difficulty"].items():
        require_type(value, int, f"timing report.summary.by_difficulty.{key}")

    deepest = summary["deepest_path"]
    require_type(deepest, dict, "timing report.summary.deepest_path")
    require_keys(deepest, ["id", "depth", "from", "to"], "timing report.summary.deepest_path")
    require_type(deepest["id"], str, "timing report.summary.deepest_path.id")
    require_type(deepest["depth"], int, "timing report.summary.deepest_path.depth")
    require_type(deepest["from"], str, "timing report.summary.deepest_path.from")
    require_type(deepest["to"], str, "timing report.summary.deepest_path.to")
