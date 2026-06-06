"""
Real vector index for symbol-to-doc mapping.
Uses Qdrant in-memory + a lightweight local TF-IDF vectoriser.
No API key, no model download, runs fully offline.
"""

from __future__ import annotations
import uuid
import re
import math
from collections import Counter
from typing import List, Dict, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)

from app.models.schemas import DocBlock, CodeSymbol

# ---------------------------------------------------------------------------
# Lightweight local TF-IDF vectoriser (no downloads required)
# ---------------------------------------------------------------------------

VECTOR_SIZE = 256   # truncated vocabulary projection


def _tokenize(text: str) -> List[str]:
    """Lower-case word tokeniser, splits on non-alphanumeric."""
    return re.findall(r"[a-z0-9_]+", text.lower())


def _hash_bucket(token: str, size: int = VECTOR_SIZE) -> int:
    """Map a token to a bucket index via FNV-1a hash."""
    h = 2166136261
    for ch in token.encode():
        h ^= ch
        h = (h * 16777619) & 0xFFFFFFFF
    return h % size


def _tfidf_vector(tokens: List[str], idf: Dict[str, float]) -> List[float]:
    """Return a hashed TF-IDF vector of length VECTOR_SIZE."""
    tf = Counter(tokens)
    total = max(len(tokens), 1)
    vec = [0.0] * VECTOR_SIZE
    for tok, count in tf.items():
        w = (count / total) * idf.get(tok, 1.0)
        bucket = _hash_bucket(tok)
        vec[bucket] += w
    # L2 normalise
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class LocalVectoriser:
    """Corpus-level IDF + per-text TF-IDF hashed embeddings."""

    def __init__(self):
        self.idf: Dict[str, float] = {}

    def fit(self, texts: List[str]) -> None:
        N = len(texts)
        df: Counter = Counter()
        for text in texts:
            unique_toks = set(_tokenize(text))
            df.update(unique_toks)
        self.idf = {
            tok: math.log(N / (1 + count))
            for tok, count in df.items()
        }

    def encode(self, texts: List[str]) -> List[List[float]]:
        return [_tfidf_vector(_tokenize(t), self.idf) for t in texts]


# ---------------------------------------------------------------------------
# Singleton client + vectoriser
# ---------------------------------------------------------------------------

_vectoriser: Optional[LocalVectoriser] = None
_client: Optional[QdrantClient] = None

COLLECTION_NAME = "doc_blocks"


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(":memory:")
        _client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    return _client


# ---------------------------------------------------------------------------
# Index operations
# ---------------------------------------------------------------------------

def index_doc_blocks(doc_blocks: List[DocBlock]) -> None:
    """Embed and store all doc blocks in Qdrant."""
    global _vectoriser
    client = _get_client()

    texts = [f"{b.section_heading}\n{b.content}" for b in doc_blocks]
    _vectoriser = LocalVectoriser()
    _vectoriser.fit(texts)
    vectors = _vectoriser.encode(texts)

    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, b.id)),
            vector=vec,
            payload={
                "block_id": b.id,
                "doc_path": b.doc_path,
                "section_heading": b.section_heading,
                "symbols": b.symbols,
            },
        )
        for b, vec in zip(doc_blocks, vectors)
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)


def find_docs_for_symbols(symbol_names: List[str], top_k: int = 10) -> List[str]:
    """
    Given changed symbol names, find doc block IDs most likely to reference them.
    Returns a list of block_id strings.
    """
    if not symbol_names or _vectoriser is None:
        return []

    client = _get_client()
    query_text = "documentation for: " + ", ".join(symbol_names)
    query_vec = _vectoriser.encode([query_text])[0]

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vec,
        limit=top_k,
        score_threshold=0.10,
    )
    return [r.payload["block_id"] for r in results]


# ---------------------------------------------------------------------------
# Explicit symbol-to-doc linking (augments embeddings)
# ---------------------------------------------------------------------------

def _extract_symbol_mentions(text: str, known_symbols: List[str]) -> List[str]:
    """Find symbol names explicitly mentioned in a doc block."""
    mentioned = []
    for sym in known_symbols:
        short = sym.split(".")[-1]
        pattern = rf"\b{re.escape(short)}\b"
        if re.search(pattern, text):
            mentioned.append(sym)
    return mentioned


# ---------------------------------------------------------------------------
# STUB — implement real embedding model support
# ---------------------------------------------------------------------------

def embed_with_model(texts: list, model: str = "text-embedding-3-small") -> list:
    """
    Encode a list of text strings into dense embedding vectors using a real
    embedding model (OpenAI, sentence-transformers, Cohere, etc.).

    This replaces the local TF-IDF vectoriser with model-quality embeddings
    for more accurate semantic symbol-to-doc linking.

    Expected return: List[List[float]] where each inner list has the same
    length as the model's embedding dimension (e.g. 1536 for OpenAI ada-002).

    TODO — implement one of these approaches:

    Option A — OpenAI embeddings (requires LLM_API_KEY in .env):
        import openai
        client = openai.OpenAI(api_key=settings.LLM_API_KEY)
        response = client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]

    Option B — sentence-transformers (runs fully offline, no API key):
        pip install sentence-transformers
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer("all-MiniLM-L6-v2")
        return encoder.encode(texts).tolist()

    After implementing, update index_doc_blocks() to call embed_with_model()
    instead of LocalVectoriser, and update VECTOR_SIZE to match the model dim.

    Reference: https://platform.openai.com/docs/guides/embeddings
    """
    # ── TODO: replace the line below with the real embedding call ──
    raise NotImplementedError(
        "embed_with_model() is not implemented. "
        "See the docstring for two implementation options (OpenAI or sentence-transformers)."
    )


def build_symbol_doc_map(
    doc_blocks: List[DocBlock],
    all_symbols: List[CodeSymbol],
) -> Dict[str, List[str]]:
    """
    Build a mapping symbol_name -> [block_ids] using explicit text mentions.
    Mutates doc_block.symbols in-place and returns the map.
    """
    symbol_names = [s.name for s in all_symbols]
    sym_to_blocks: Dict[str, List[str]] = {n: [] for n in symbol_names}

    for block in doc_blocks:
        mentions = _extract_symbol_mentions(
            block.section_heading + " " + block.content, symbol_names
        )
        # For methods, also link the parent class
        extra = []
        for m in mentions:
            if "." in m:
                cls = m.split(".")[0]
                if cls in symbol_names:
                    extra.append(cls)
        mentions = list(set(mentions + extra))
        block.symbols = mentions
        for sym in mentions:
            if sym in sym_to_blocks:
                sym_to_blocks[sym].append(block.id)

    return sym_to_blocks
