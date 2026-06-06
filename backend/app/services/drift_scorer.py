"""
Drift scoring engine.
Computes a 0-100 staleness score for each doc block based on
how many of the symbols it references have changed and how recently.
No mocking – pure computation.
"""

from __future__ import annotations
from typing import List, Dict
from datetime import datetime, timezone
import math

from app.models.schemas import DocBlock, DriftResult, CodeSymbol


# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

# Recency decay half-life in days (score halves every N days of age)
RECENCY_HALF_LIFE_DAYS = 30

# Weight for symbol-coverage ratio vs recency
SYMBOL_WEIGHT = 0.65
RECENCY_WEIGHT = 0.35

# Threshold to flag as "stale"
STALE_THRESHOLD = 40.0
CRITICAL_THRESHOLD = 70.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recency_factor(changed_at: datetime) -> float:
    """
    Returns 1.0 for changes right now, decaying exponentially.
    Uses half-life of RECENCY_HALF_LIFE_DAYS.
    """
    now = datetime.now(timezone.utc)
    if changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - changed_at).total_seconds() / 86400)
    return math.exp(-math.log(2) * age_days / RECENCY_HALF_LIFE_DAYS)


def _symbol_coverage(doc_symbols: List[str], changed_symbol_names: List[str]) -> float:
    """
    Fraction of the doc block's referenced symbols that have changed.
    Returns 0.0 if the doc references no symbols.
    """
    if not doc_symbols:
        return 0.0
    changed_set = set(changed_symbol_names)
    hits = sum(1 for s in doc_symbols if s in changed_set)
    return hits / len(doc_symbols)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_drift(
    doc_block: DocBlock,
    changed_symbol_names: List[str],
    changed_at: datetime,
) -> float:
    """
    Compute a drift score (0-100) for a single doc block.

    Higher score = more stale.

    Formula:
      base = (hit_count / total_symbols)^0.5   – square-root softens low coverage
      recency = exponential decay over RECENCY_HALF_LIFE_DAYS
      score = 100 * (SYMBOL_WEIGHT * base + RECENCY_WEIGHT * recency)
              clamped to [0, 100]
    """
    if not doc_block.symbols:
        return 0.0

    changed_set = set(changed_symbol_names)
    hit_count = sum(1 for s in doc_block.symbols if s in changed_set)
    if hit_count == 0:
        return 0.0

    # Soften: sqrt(hits/total) so even one hit on a large block scores meaningfully
    coverage = math.sqrt(hit_count / len(doc_block.symbols))
    recency = _recency_factor(changed_at)

    raw = SYMBOL_WEIGHT * coverage + RECENCY_WEIGHT * recency
    score = min(100.0, raw * 100.0)
    return round(score, 1)


def score_all_blocks(
    doc_blocks: List[DocBlock],
    changed_symbol_names: List[str],
    changed_at: datetime,
) -> List[DriftResult]:
    """
    Score every doc block against the changed symbol set.
    Returns DriftResult list sorted by drift_score descending.
    """
    results: List[DriftResult] = []
    changed_set = set(changed_symbol_names)

    for block in doc_blocks:
        affected = [s for s in block.symbols if s in changed_set]
        if not affected:
            # Doc doesn't reference any changed symbol – score 0
            score = 0.0
        else:
            score = score_drift(block, changed_symbol_names, changed_at)

        results.append(
            DriftResult(
                doc_block_id=block.id,
                doc_path=block.doc_path,
                section_heading=block.section_heading,
                drift_score=score,
                changed_symbols=affected,
                original_content=block.content,
            )
        )

    results.sort(key=lambda r: r.drift_score, reverse=True)
    return results


def compute_repo_freshness(drift_results: List[DriftResult]) -> float:
    """
    Aggregate freshness score for a repo (0=totally stale, 100=fresh).
    """
    if not drift_results:
        return 100.0
    avg_staleness = sum(r.drift_score for r in drift_results) / len(drift_results)
    return round(100.0 - avg_staleness, 1)
