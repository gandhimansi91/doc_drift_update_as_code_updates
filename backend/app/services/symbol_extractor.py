"""
Real tree-sitter symbol extraction.
Parses Python files into an AST and extracts functions, classes, and methods.
No mocking – this runs locally with the tree-sitter library.
"""

from __future__ import annotations
import os
from typing import List, Optional
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node

from app.models.schemas import CodeSymbol

PY_LANGUAGE = Language(tspython.language(), "python")
_parser = Parser()
_parser.set_language(PY_LANGUAGE)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _get_docstring(body_node: Node, source: bytes) -> Optional[str]:
    """Return the first string literal in a function/class body as docstring."""
    for child in body_node.children:
        if child.type == "expression_statement":
            for sub in child.children:
                if sub.type == "string":
                    raw = _node_text(sub, source).strip()
                    # Strip triple-quote delimiters
                    for q in ('"""', "'''", '"', "'"):
                        if raw.startswith(q) and raw.endswith(q) and len(raw) > 2 * len(q):
                            return raw[len(q):-len(q)].strip()
                    return raw
        # Stop at first non-docstring statement
        if child.type not in ("comment", "expression_statement", "string"):
            break
    return None


def _get_signature(node: Node, source: bytes) -> str:
    """Return everything up to the colon for functions/classes."""
    lines = _node_text(node, source).split("\n")
    sig_lines = []
    for line in lines:
        sig_lines.append(line)
        if line.rstrip().endswith(":"):
            break
    return "\n".join(sig_lines)


# ---------------------------------------------------------------------------
# AST walker
# ---------------------------------------------------------------------------

def _walk_node(
    node: Node,
    source: bytes,
    file_path: str,
    symbols: List[CodeSymbol],
    class_name: Optional[str] = None,
):
    """Recursively walk the AST and collect symbol definitions."""
    if node.type in ("function_definition", "decorated_definition"):
        actual = node
        if node.type == "decorated_definition":
            # Find the inner function/class
            for child in node.children:
                if child.type in ("function_definition", "class_definition"):
                    actual = child
                    break

        if actual.type == "function_definition":
            name_node = actual.child_by_field_name("name")
            body_node = actual.child_by_field_name("body")
            name = _node_text(name_node, source) if name_node else "unknown"
            docstring = _get_docstring(body_node, source) if body_node else None
            signature = _get_signature(actual, source)

            kind = "method" if class_name else "function"
            full_name = f"{class_name}.{name}" if class_name else name

            symbols.append(
                CodeSymbol(
                    name=full_name,
                    kind=kind,
                    file_path=file_path,
                    start_line=actual.start_point[0] + 1,
                    end_line=actual.end_point[0] + 1,
                    signature=signature,
                    docstring=docstring,
                )
            )
            # Recurse into nested functions
            if body_node:
                for child in body_node.children:
                    _walk_node(child, source, file_path, symbols, class_name)
            return

    if node.type == "class_definition":
        name_node = node.child_by_field_name("name")
        body_node = node.child_by_field_name("body")
        name = _node_text(name_node, source) if name_node else "unknown"
        docstring = _get_docstring(body_node, source) if body_node else None

        symbols.append(
            CodeSymbol(
                name=name,
                kind="class",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                signature=f"class {name}:",
                docstring=docstring,
            )
        )

        # Walk class body for methods
        if body_node:
            for child in body_node.children:
                _walk_node(child, source, file_path, symbols, class_name=name)
        return

    # Generic recursion
    for child in node.children:
        _walk_node(child, source, file_path, symbols, class_name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_symbols_from_file(file_path: str) -> List[CodeSymbol]:
    """Parse a Python file and return all top-level symbols."""
    path = Path(file_path)
    if not path.exists():
        return []
    source = path.read_bytes()
    tree = _parser.parse(source)
    symbols: List[CodeSymbol] = []
    _walk_node(tree.root_node, source, str(path), symbols)
    return symbols


def extract_symbols_from_source(source_code: str, virtual_path: str = "<string>") -> List[CodeSymbol]:
    """Parse a Python source string (used for diff patching)."""
    source = source_code.encode("utf-8")
    tree = _parser.parse(source)
    symbols: List[CodeSymbol] = []
    _walk_node(tree.root_node, source, virtual_path, symbols)
    return symbols


def extract_symbols_from_directory(directory: str) -> List[CodeSymbol]:
    """Recursively extract symbols from all .py files in a directory."""
    all_symbols: List[CodeSymbol] = []
    for root, _, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".py"):
                all_symbols.extend(extract_symbols_from_file(os.path.join(root, fname)))
    return all_symbols


def extract_symbols_from_diff_text(diff_patch: str) -> List[str]:
    """
    Extract symbol names from a unified diff without needing the actual file on disk.
    Finds Python function/class definitions in added or context lines.
    Used for real GitHub repos where we only have the patch, not the local file.
    """
    import re
    symbols: List[str] = []
    for line in diff_patch.split("\n"):
        if line.startswith("\\"):
            continue  # "No newline at end of file" markers
        content = line[1:].strip() if line and line[0] in "+-" else line.strip()
        m = re.match(r"(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*[\(:]", content)
        if m:
            symbols.append(m.group(1))
        m = re.match(r"class\s+([a-zA-Z_]\w*)\s*[:(]", content)
        if m:
            symbols.append(m.group(1))
    # deduplicate, preserve order
    seen: set = set()
    deduped = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def extract_changed_symbols(diff_patch: str, file_path: str) -> List[str]:
    """
    Given a unified diff patch, return the names of symbols whose lines were touched.
    We reconstruct the new file content from the patch and re-parse.
    This is a best-effort approach – returns symbol names (strings).
    """
    changed_lines: set[int] = set()
    current_new_line = 0

    for line in diff_patch.split("\n"):
        if line.startswith("@@"):
            # Parse @@ -old +new @@ header
            try:
                parts = line.split("+")[1].split("@@")[0].strip()
                start = int(parts.split(",")[0])
                current_new_line = start
            except (IndexError, ValueError):
                pass
        elif line.startswith("+") and not line.startswith("+++"):
            changed_lines.add(current_new_line)
            current_new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            changed_lines.add(current_new_line)
            # Don't advance new line counter
        else:
            current_new_line += 1

    # Extract symbols from the actual file and filter to those touching changed lines
    symbols = extract_symbols_from_file(file_path)
    touched = []
    for sym in symbols:
        sym_lines = set(range(sym.start_line, sym.end_line + 1))
        if sym_lines & changed_lines:
            touched.append(sym.name)

    return touched if touched else [s.name for s in symbols]  # fallback: all
