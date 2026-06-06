"""
Parse Markdown documentation files into DocBlock objects.
Splits on heading boundaries and assigns stable IDs.
"""

from __future__ import annotations
import hashlib
import re
from pathlib import Path
from typing import List
from datetime import datetime, timezone

from app.models.schemas import DocBlock


def _stable_id(doc_path: str, heading: str) -> str:
    key = f"{doc_path}::{heading}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def parse_doc_file(file_path: str, read_counts: dict | None = None) -> List[DocBlock]:
    """
    Split a Markdown file into DocBlock objects at each heading boundary.
    read_counts: optional dict of section_heading -> int for mock page-view data.
    """
    path = Path(file_path)
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    blocks: List[DocBlock] = []

    # Split on headings (## or ###)
    sections = re.split(r"(?m)^(#{1,4}\s+.+)$", text)

    current_heading = "_preamble"
    current_content = ""

    def flush():
        nonlocal current_heading, current_content
        content = current_content.strip()
        if content:
            rc = (read_counts or {}).get(current_heading, 0)
            blocks.append(
                DocBlock(
                    id=_stable_id(file_path, current_heading),
                    doc_path=str(path),
                    section_heading=current_heading,
                    content=content,
                    symbols=[],
                    read_count=rc,
                    last_updated=datetime(2024, 1, 10, tzinfo=timezone.utc),
                )
            )
        current_content = ""

    for chunk in sections:
        if re.match(r"^#{1,4}\s+", chunk):
            flush()
            current_heading = chunk.strip()
        else:
            current_content += chunk

    flush()
    return blocks


def parse_all_docs(docs_dir: str, read_counts: dict | None = None) -> List[DocBlock]:
    """Parse all .md files in a directory."""
    all_blocks: List[DocBlock] = []
    for md_file in Path(docs_dir).rglob("*.md"):
        all_blocks.extend(parse_doc_file(str(md_file), read_counts))
    return all_blocks


def parse_doc_content(content: str, path: str, read_counts: dict | None = None) -> List[DocBlock]:
    """Parse a markdown string (not a file) into DocBlock objects."""
    blocks: List[DocBlock] = []
    sections = re.split(r"(?m)^(#{1,4}\s+.+)$", content)

    current_heading = "_preamble"
    current_content = ""

    def flush() -> None:
        nonlocal current_heading, current_content
        c = current_content.strip()
        if c:
            rc = (read_counts or {}).get(current_heading, 0)
            blocks.append(DocBlock(
                id=_stable_id(path, current_heading),
                doc_path=path,
                section_heading=current_heading,
                content=c,
                symbols=[],
                read_count=rc,
                last_updated=datetime(2024, 1, 10, tzinfo=timezone.utc),
            ))
        current_content = ""

    for chunk in sections:
        if re.match(r"^#{1,4}\s+", chunk):
            flush()
            current_heading = chunk.strip()
        else:
            current_content += chunk

    flush()
    return blocks


def parse_docs_from_dict(
    docs: dict,  # {path: markdown_content}
    read_counts: dict | None = None,
) -> List[DocBlock]:
    """Parse a dict of {path: content} into DocBlock objects (no filesystem access)."""
    all_blocks: List[DocBlock] = []
    for path, content in docs.items():
        all_blocks.extend(parse_doc_content(content, path, read_counts))
    return all_blocks
