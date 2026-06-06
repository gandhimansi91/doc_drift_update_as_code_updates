"""
Executable doc example verification.

STATUS: 🔶 STUB
  All functions return empty / placeholder results. No code is executed.

This service verifies that code snippets embedded in markdown documentation
still run correctly against the current codebase. It catches the common case
where a function signature changes but the example in the README is never updated.

Pipeline:
  1. extract_code_blocks()  — parse all ```python blocks from a doc section
  2. execute_code_block()   — run each block in a sandbox and capture output/errors
  3. verify_doc_examples()  — return a list of VerificationResult objects

TODO:
  Implement execute_code_block() using subprocess + a timeout.
  Wire verify_doc_examples() into the analysis pipeline — call it in
  analysis_worker.py after step 3 (doc parsing) and include results in DriftResult.
"""

from __future__ import annotations
import logging
import re
import textwrap
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Safety timeout for running untrusted code
EXECUTION_TIMEOUT_SECONDS = 5


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CodeBlock:
    """A fenced code block extracted from a doc section."""
    language: str           # e.g. "python", "bash", "javascript"
    source: str             # raw source code from the markdown fence
    doc_path: str
    section_heading: str
    line_number: int = 0


@dataclass
class VerificationResult:
    """Outcome of running one code block."""
    code_block: CodeBlock
    passed: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Step 1 — Extract code blocks from markdown
# ---------------------------------------------------------------------------

def extract_code_blocks(content: str, doc_path: str, section_heading: str) -> List[CodeBlock]:
    """
    Parse all fenced code blocks from a markdown string.

    Finds blocks of the form:
        ```python
        some_code()
        ```

    Returns a list of CodeBlock objects for each fenced block found.

    TODO:
      The regex below is a starting point. Extend it to handle:
        - Indented fences (4-space or tab-indented code blocks)
        - Nested fences (rare but valid)
        - Line number tracking (set CodeBlock.line_number)
    """
    pattern = re.compile(
        r"```(?P<lang>[a-zA-Z0-9_+-]*)\n(?P<code>.*?)```",
        re.DOTALL,
    )
    blocks = []
    for i, match in enumerate(pattern.finditer(content)):
        lang = match.group("lang").strip() or "text"
        code = textwrap.dedent(match.group("code"))
        blocks.append(CodeBlock(
            language=lang,
            source=code,
            doc_path=doc_path,
            section_heading=section_heading,
            line_number=content[:match.start()].count("\n") + 1,
        ))
    return blocks


# ---------------------------------------------------------------------------
# Step 2 — Execute a single code block (STUB)
# ---------------------------------------------------------------------------

async def execute_code_block(block: CodeBlock) -> VerificationResult:
    """
    Run a code block in a sandboxed subprocess and return the result.

    Currently returns a placeholder VerificationResult with passed=False.

    TODO — implement safe execution:

    For Python blocks:
        import asyncio, tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(block.source)
            tmp_path = f.name
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=EXECUTION_TIMEOUT_SECONDS
            )
            return VerificationResult(
                code_block=block,
                passed=(proc.returncode == 0),
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                exit_code=proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            return VerificationResult(
                code_block=block, passed=False,
                error_message=f"Timed out after {EXECUTION_TIMEOUT_SECONDS}s",
            )
        finally:
            os.unlink(tmp_path)

    For bash blocks: replace "python3" with "/bin/bash"
    For other languages: return passed=True (skip execution) or add more runtimes.

    IMPORTANT SECURITY NOTE:
      Never execute untrusted code without sandboxing. In production, use
      Docker (--network none --memory 64m --cpus 0.5) or a WASM runtime.
    """
    # ── TODO: implement sandboxed execution ──
    return VerificationResult(
        code_block=block,
        passed=False,
        error_message=(
            "execute_code_block() is not implemented. "
            "See the docstring for a subprocess-based implementation."
        ),
    )


# ---------------------------------------------------------------------------
# Step 3 — Verify all code examples in a doc section (STUB)
# ---------------------------------------------------------------------------

async def verify_doc_examples(
    content: str,
    doc_path: str,
    section_heading: str,
    languages: Optional[List[str]] = None,  # None = all; ["python"] = Python only
) -> List[VerificationResult]:
    """
    Extract and execute all code blocks in a doc section.

    Returns a list of VerificationResult — one per code block found.
    Currently returns an empty list because execute_code_block() is a stub.

    TODO:
      1. Call extract_code_blocks() to get all blocks
      2. Filter by `languages` if provided
      3. Call execute_code_block() for each block (use asyncio.gather for parallelism)
      4. Return the results list

    Wire this into analysis_worker.py step 3 (after parse_all_docs):
        for block in doc_blocks:
            results = await verify_doc_examples(
                block.content, block.doc_path, block.section_heading,
                languages=["python"]
            )
            failed = [r for r in results if not r.passed]
            # Add failed examples as extra evidence for drift scoring
    """
    # ── TODO: implement example extraction + execution ──
    blocks = extract_code_blocks(content, doc_path, section_heading)
    if not blocks:
        return []

    # TODO: filter by languages, execute in parallel, return real results
    return []   # placeholder — replace with: await asyncio.gather(*[execute_code_block(b) for b in blocks])
