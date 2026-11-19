#!/usr/bin/env python3
"""Validate living specifications under docs/specs/."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FEATURE_FILENAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.md$")
VALID_STATUSES = {"active", "experimental", "deprecated"}
ALLOWED_FRONTMATTER_KEYS = {
    "feature",
    "title",
    "status",
    "packages",
    "source_files",
    "tests",
}
REQUIRED_FRONTMATTER_KEYS = {"feature", "title", "status", "packages", "source_files"}
REQUIRED_HEADINGS = (
    "## 1. Overview",
    "## 2. Requirements & Behavior",
    "## 3. Interfaces & Contracts",
    "## 4. Edge Cases & Failure Modes",
    "## 5. Verification",
)

INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)*?\1")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")


def _strip_yaml_comment(raw: str) -> str:
    """Strip an inline YAML comment preceded by whitespace when outside quotes."""
    in_quote: str | None = None
    for idx, ch in enumerate(raw):
        if ch in {"'", '"'}:
            if in_quote is None:
                in_quote = ch
            elif in_quote == ch:
                in_quote = None
        elif ch == "#" and in_quote is None and (idx == 0 or raw[idx - 1].isspace()):
            return raw[:idx].rstrip()
    return raw.rstrip()


def _clean_scalar(raw: str) -> str:
    value = _strip_yaml_comment(raw).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, str | list[str]], str]:
    """Parse strict subset of YAML frontmatter from a markdown document."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing YAML frontmatter opening '---' on line 1")

    end_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        raise ValueError("Unclosed YAML frontmatter (missing closing '---')")

    data: dict[str, str | list[str]] = {}
    current_list_key: str | None = None

    for line_no, raw_line in enumerate(lines[1:end_idx], start=2):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if raw_line.startswith((" ", "\t")) or stripped.startswith("- "):
            if not stripped.startswith("- "):
                raise ValueError(f"Frontmatter line {line_no}: unexpected indentation '{raw_line}'")
            if current_list_key is None:
                raise ValueError(f"Frontmatter line {line_no}: list item without parent key")
            item = _clean_scalar(stripped[2:])
            if not item:
                raise ValueError(f"Frontmatter line {line_no}: empty list item for '{current_list_key}'")
            existing = data[current_list_key]
            assert isinstance(existing, list)
            existing.append(item)
            continue

        if ":" not in raw_line:
            raise ValueError(f"Frontmatter line {line_no}: expected 'key: value', got '{raw_line}'")

        key_raw, val_raw = raw_line.split(":", 1)
        key = key_raw.strip()
        if not key:
            raise ValueError(f"Frontmatter line {line_no}: empty key")
        if key not in ALLOWED_FRONTMATTER_KEYS:
            raise ValueError(f"Frontmatter line {line_no}: unknown key '{key}'")
        if key in data:
            raise ValueError(f"Frontmatter line {line_no}: duplicate key '{key}'")

        val_clean = _strip_yaml_comment(val_raw).strip()
        if val_clean == "":
            data[key] = []
            current_list_key = key
        elif val_clean == "[]":
            data[key] = []
            current_list_key = None
        elif val_clean.startswith("[") and val_clean.endswith("]"):
            inner = val_clean[1:-1].strip()
            items = [_clean_scalar(part) for part in inner.split(",") if _clean_scalar(part)]
            data[key] = items
            current_list_key = None
        else:
            data[key] = _clean_scalar(val_raw)
            current_list_key = None

    body = "\n".join(lines[end_idx + 1 :])
    return data, body


def _iter_non_fenced_lines(text: str) -> list[str]:
    """Return markdown lines outside fenced code blocks."""
    out: list[str] = []
    fence_char: str | None = None
    fence_len = 0

    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence_char is None:
                fence_char = marker[0]
                fence_len = len(marker)
                continue
            if marker[0] == fence_char and len(marker) >= fence_len and line.strip() == marker:
                fence_char = None
                fence_len = 0
                continue
        if fence_char is None:
            out.append(line)

    return out


def extract_headings(text: str) -> set[str]:
    """Extract level-2 markdown headings outside fenced code blocks."""
    headings: set[str] = set()
    for line in _iter_non_fenced_lines(text):
        stripped = line.strip()
        if stripped.startswith("## "):
            headings.add(stripped)
    return headings


def extract_markdown_links(text: str) -> list[str]:
    """Extract markdown link targets outside fenced code blocks and inline code."""
    targets: list[str] = []
    for line in _iter_non_fenced_lines(text):
        cleaned = INLINE_CODE_RE.sub("", line)
        for match in MARKDOWN_LINK_RE.finditer(cleaned):
            target = match.group(1).strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1].strip()
            targets.append(target)
    return targets


def _resolve_repo_path(root_resolved: Path, raw_path: str) -> Path:
    """Resolve a repo-relative path and ensure it stays within root."""
    candidate_input = Path(raw_path)
    if candidate_input.is_absolute():
        raise ValueError(f"path '{raw_path}' must be relative to the repository root")
    resolved = (root_resolved / candidate_input).resolve()
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"path '{raw_path}' escapes repository root")
    return resolved


def validate_repo(root: Path) -> list[str]:
    """Run all living specification checks against `root` and return error messages."""
    errors: list[str] = []
    root_resolved = root.resolve()

    specs_dir = root / "docs" / "specs"
    readme_path = specs_dir / "README.md"
    arch_path = specs_dir / "architecture.md"
    template_path = specs_dir / "templates" / "feature_spec_template.md"
    features_dir = specs_dir / "features"
    legacy_contracts_dir = specs_dir / "contracts"

    for required_file in (readme_path, arch_path, template_path):
        if not required_file.is_file():
            errors.append(f"Missing required spec file: {required_file.relative_to(root)}")

    if legacy_contracts_dir.exists():
        errors.append("Legacy directory 'docs/specs/contracts' must be removed")

    if not features_dir.is_dir():
        errors.append("Missing required directory: docs/specs/features")
        return errors

    feature_files = sorted(features_dir.glob("*.md"))
    if not feature_files:
        errors.append("No living feature specifications found in docs/specs/features/")
        return errors

    # Validate template headings
    if template_path.is_file():
        template_headings = extract_headings(template_path.read_text(encoding="utf-8"))
        for heading in REQUIRED_HEADINGS:
            if heading not in template_headings:
                errors.append(
                    f"docs/specs/templates/feature_spec_template.md: missing required heading '{heading}'"
                )

    # Validate each living feature spec
    for spec_path in feature_files:
        rel_spec = spec_path.relative_to(root).as_posix()

        if not FEATURE_FILENAME_RE.match(spec_path.name):
            errors.append(
                f"{rel_spec}: filename must be lowercase kebab-case without numeric prefixes "
                f"(expected pattern {FEATURE_FILENAME_RE.pattern})"
            )

        content = spec_path.read_text(encoding="utf-8")
        try:
            fm, body = parse_frontmatter(content)
        except ValueError as exc:
            errors.append(f"{rel_spec}: {exc}")
            continue

        missing_keys = sorted(REQUIRED_FRONTMATTER_KEYS - set(fm.keys()))
        if missing_keys:
            errors.append(f"{rel_spec}: missing required frontmatter keys: {', '.join(missing_keys)}")
            continue

        feature_slug = fm["feature"]
        if not isinstance(feature_slug, str) or feature_slug != spec_path.stem:
            errors.append(
                f"{rel_spec}: frontmatter 'feature' ({feature_slug!r}) must match filename stem '{spec_path.stem}'"
            )

        title = fm["title"]
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{rel_spec}: frontmatter 'title' must be a non-empty string")

        status = fm["status"]
        if not isinstance(status, str) or status not in VALID_STATUSES:
            errors.append(
                f"{rel_spec}: frontmatter 'status' must be one of {sorted(VALID_STATUSES)}, got {status!r}"
            )

        packages = fm["packages"]
        if not isinstance(packages, list) or not packages:
            errors.append(f"{rel_spec}: frontmatter 'packages' must be a non-empty list")
        else:
            for pkg in packages:
                try:
                    resolved = _resolve_repo_path(root_resolved, pkg)
                except ValueError as exc:
                    errors.append(f"{rel_spec}: packages entry '{pkg}' invalid ({exc})")
                    continue
                if not resolved.is_dir():
                    errors.append(f"{rel_spec}: packages directory does not exist: '{pkg}'")

        source_files = fm["source_files"]
        if not isinstance(source_files, list) or not source_files:
            errors.append(f"{rel_spec}: frontmatter 'source_files' must be a non-empty list")
        else:
            for src in source_files:
                try:
                    resolved = _resolve_repo_path(root_resolved, src)
                except ValueError as exc:
                    errors.append(f"{rel_spec}: source_files entry '{src}' invalid ({exc})")
                    continue
                if not resolved.is_file():
                    errors.append(f"{rel_spec}: source file does not exist: '{src}'")

        if "tests" in fm:
            tests = fm["tests"]
            if not isinstance(tests, list):
                errors.append(f"{rel_spec}: frontmatter 'tests' must be a list")
            else:
                for test_path in tests:
                    try:
                        resolved = _resolve_repo_path(root_resolved, test_path)
                    except ValueError as exc:
                        errors.append(f"{rel_spec}: tests entry '{test_path}' invalid ({exc})")
                        continue
                    if not resolved.is_file():
                        errors.append(f"{rel_spec}: test file does not exist: '{test_path}'")

        headings = extract_headings(body)
        for heading in REQUIRED_HEADINGS:
            if heading not in headings:
                errors.append(f"{rel_spec}: missing required heading '{heading}'")

    # Validate bidirectional Feature Catalog sync in docs/specs/README.md
    if readme_path.is_file():
        readme_text = readme_path.read_text(encoding="utf-8")
        catalog_features: set[str] = set()
        for target in extract_markdown_links(readme_text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0]
            if path_part.startswith("./"):
                path_part = path_part[2:]
            if path_part.startswith("features/") and path_part.endswith(".md"):
                catalog_features.add(path_part[len("features/") :])

        disk_feature_names = {p.name for p in feature_files}
        missing_from_catalog = sorted(disk_feature_names - catalog_features)
        missing_from_disk = sorted(catalog_features - disk_feature_names)

        for name in missing_from_catalog:
            errors.append(
                f"docs/specs/README.md: feature spec 'features/{name}' is missing from the Feature Catalog"
            )
        for name in missing_from_disk:
            errors.append(
                f"docs/specs/README.md: catalog link 'features/{name}' points to a missing feature spec"
            )

    # Validate all relative markdown links across README.md, architecture.md, and features/*.md
    docs_to_link_check: list[Path] = []
    if readme_path.is_file():
        docs_to_link_check.append(readme_path)
    if arch_path.is_file():
        docs_to_link_check.append(arch_path)
    docs_to_link_check.extend(feature_files)

    for doc_path in docs_to_link_check:
        rel_doc = doc_path.relative_to(root).as_posix()
        doc_text = doc_path.read_text(encoding="utf-8")
        for target in extract_markdown_links(doc_text):
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            if path_part.startswith("/"):
                errors.append(f"{rel_doc}: relative link expected, got absolute path '{target}'")
                continue
            resolved = (doc_path.parent / path_part).resolve()
            if not resolved.is_relative_to(root_resolved):
                errors.append(f"{rel_doc}: link '{target}' escapes repository root")
                continue
            if not resolved.exists():
                errors.append(f"{rel_doc}: broken relative link '{target}'")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate living specs under docs/specs/.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root directory (defaults to script parent directory).",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    errors = validate_repo(root)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(f"Living spec validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    feature_count = len(list((root / "docs" / "specs" / "features").glob("*.md")))
    print(
        f"Validated {feature_count} living feature spec(s), architecture.md, README.md, "
        f"and feature_spec_template.md (0 errors)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

