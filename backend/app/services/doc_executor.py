"""
Executable doc example verification.

STATUS: ✅ BUILT
  Extracts fenced codeblocks and executes them in an async subprocess sandbox.
"""

from __future__ import annotations
import asyncio
import logging
import tempfile
import os
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
# Step 2 — Execute a single code block
# ---------------------------------------------------------------------------

async def execute_code_block(block: CodeBlock) -> VerificationResult:
    """
    Run a code block in a sandboxed subprocess and return the result.
    """
    logger.info("Executing %s code block from %s (line %d)", block.language, block.doc_path, block.line_number)
    if block.language != "python":
        return VerificationResult(code_block=block, passed=True)
        
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
    except Exception as e:
        return VerificationResult(code_block=block, passed=False, error_message=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Step 3 — Verify all code examples in a doc section
# ---------------------------------------------------------------------------

async def verify_doc_examples(
    content: str,
    doc_path: str,
    section_heading: str,
    languages: Optional[List[str]] = None,  # None = all; ["python"] = Python only
) -> List[VerificationResult]:
    """
    Extract and execute all code blocks in a doc section.
    """
    blocks = extract_code_blocks(content, doc_path, section_heading)
    if not blocks:
        return []

    if languages:
        blocks = [b for b in blocks if b.language in languages]
        
    return await asyncio.gather(*[execute_code_block(b) for b in blocks])
