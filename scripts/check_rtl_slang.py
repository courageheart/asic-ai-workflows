#!/usr/bin/env python3

from __future__ import annotations

import shlex
import sys
from pathlib import Path

try:
    import pyslang as ps
except ImportError as exc:
    print("rtl slang check failed:")
    print(f"- pyslang is not installed: {exc}")
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
RTL_SUFFIXES = {".sv", ".v"}
FILELIST_SUFFIX = ".f"
IGNORED_DIRS = {".git", "__pycache__", "obj_dir"}


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def find_files(*, suffixes: set[str]) -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or should_ignore(path):
            continue
        if path.suffix in suffixes:
            paths.append(path)
    return sorted(paths)


def split_filelist_line(line: str) -> list[str]:
    raw = line.split("//", 1)[0].strip()
    if not raw or raw.startswith("#"):
        return []
    return shlex.split(raw)


def resolve_nested_filelist(token: str, base_dir: Path, current_dir: Path) -> Path:
    nested = Path(token)
    if not nested.is_absolute():
        if base_dir == ROOT:
            nested = ROOT / nested
        else:
            nested = current_dir / nested
    return nested.resolve()


def resolve_source_file(token: str, current_dir: Path) -> Path:
    source = Path(token)
    if not source.is_absolute():
        source = current_dir / source
    return source.resolve()


def parse_filelist(path: Path, seen: set[Path] | None = None) -> set[Path]:
    if seen is None:
        seen = set()
    if path in seen:
        return set()
    seen.add(path)

    referenced: set[Path] = set()
    current_dir = path.parent

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        tokens = split_filelist_line(raw_line)
        if not tokens:
            continue

        index = 0
        while index < len(tokens):
            token = tokens[index]

            if token in {"-f", "-F"}:
                index += 1
                if index >= len(tokens):
                    raise ValueError(f"{path.relative_to(ROOT)} has {token} without a following filelist path")
                base_dir = ROOT if token == "-f" else current_dir
                nested_path = resolve_nested_filelist(tokens[index], base_dir, current_dir)
                referenced.update(parse_filelist(nested_path, seen))
            elif token.endswith(FILELIST_SUFFIX):
                nested_path = resolve_nested_filelist(token, current_dir, current_dir)
                referenced.update(parse_filelist(nested_path, seen))
            elif Path(token).suffix in RTL_SUFFIXES:
                referenced.add(resolve_source_file(token, current_dir))

            index += 1

    return referenced


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def diagnose_unit(files: list[str]) -> tuple[int, str]:
    source_manager = ps.SourceManager()
    if len(files) == 1:
        tree = ps.SyntaxTree.fromFile(files[0], source_manager)
    else:
        tree = ps.SyntaxTree.fromFiles(files, source_manager)

    compilation = ps.Compilation()
    compilation.addSyntaxTree(tree)
    diagnostics = list(compilation.getAllDiagnostics())
    rendered = ps.DiagnosticEngine.reportAll(source_manager, diagnostics).strip()
    engine = ps.DiagnosticEngine(source_manager)
    error_count = 0
    for diagnostic in diagnostics:
        severity = engine.getSeverity(diagnostic.code, diagnostic.location)
        if severity in {ps.DiagnosticSeverity.Error, ps.DiagnosticSeverity.Fatal}:
            error_count += 1
    return error_count, rendered


def main() -> int:
    source_files = find_files(suffixes=RTL_SUFFIXES)
    filelists = find_files(suffixes={FILELIST_SUFFIX})

    source_set = {path.resolve() for path in source_files}
    filelist_coverage: dict[Path, set[Path]] = {}
    errors: list[str] = []

    for filelist in filelists:
        try:
            referenced = parse_filelist(filelist.resolve())
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue

        if not referenced:
            errors.append(f"{relpath(filelist)} does not reference any .sv or .v files")
            continue

        missing = sorted(path for path in referenced if not path.exists())
        for missing_path in missing:
            errors.append(f"{relpath(filelist)} references missing RTL file: {missing_path}")

        unknown = sorted(path for path in referenced if path.exists() and path not in source_set)
        for unknown_path in unknown:
            errors.append(f"{relpath(filelist)} references RTL outside repo scan set: {unknown_path}")

        filelist_coverage[filelist.resolve()] = {path for path in referenced if path in source_set}

    if errors:
        print("rtl slang check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    covered_sources: set[Path] = set()
    for referenced in filelist_coverage.values():
        covered_sources.update(referenced)

    standalone_sources = sorted(path for path in source_set if path not in covered_sources)

    error_findings: list[tuple[str, str]] = []
    warning_findings: list[tuple[str, str]] = []

    for filelist in sorted(filelist_coverage):
        files = [relpath(path) for path in sorted(filelist_coverage[filelist])]
        error_count, rendered = diagnose_unit(files)
        if rendered:
            if error_count:
                error_findings.append((relpath(filelist), rendered))
            else:
                warning_findings.append((relpath(filelist), rendered))

    for source in standalone_sources:
        error_count, rendered = diagnose_unit([relpath(source)])
        if rendered:
            if error_count:
                error_findings.append((relpath(source), rendered))
            else:
                warning_findings.append((relpath(source), rendered))

    if warning_findings:
        print("rtl slang check reported warnings:")
        for name, rendered in warning_findings:
            print(f"- {name}")
            for line in rendered.splitlines():
                print(f"  {line}")

    if error_findings:
        print("rtl slang check failed with errors:")
        for name, rendered in error_findings:
            print(f"- {name}")
            for line in rendered.splitlines():
                print(f"  {line}")
        return 1

    total_units = len(filelist_coverage) + len(standalone_sources)
    print(
        "rtl slang check passed "
        f"for {total_units} compile units covering {len(source_set)} Verilog/SystemVerilog files"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
