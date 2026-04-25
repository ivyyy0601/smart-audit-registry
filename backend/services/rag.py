"""
RAG (Retrieval-Augmented Generation) service.

Loads the ConsenSys smart contract security knowledge base,
embeds it with OpenAI, stores in FAISS, and retrieves
relevant context for each function being audited.

Index is built once on first run and cached to rag_index/.
"""
import os
import json
import numpy as np
from pathlib import Path
from typing import List, Optional
from openai import OpenAI

KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "knowledge_base"
INDEX_DIR          = Path(__file__).parent.parent / "rag_index"
EMBEDDING_MODEL    = "text-embedding-3-small"   # cheap, 1536-dim
CHUNK_SIZE         = 800                         # characters per chunk
CHUNK_OVERLAP      = 100


def _chunk_text(text: str) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 60]


def _load_knowledge_base() -> List[str]:
    """Read all .md files from the knowledge base directory."""
    chunks = []
    for path in sorted(KNOWLEDGE_BASE_DIR.rglob("*.md")):
        try:
            text = path.read_text(errors="ignore").strip()
            if not text:
                continue
            header = f"[Source: {path.stem}]\n"
            for chunk in _chunk_text(header + text):
                chunks.append(chunk)
        except Exception:
            pass
    return chunks


class RAGRetriever:
    """FAISS-backed knowledge retriever for smart contract vulnerabilities."""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.chunks: List[str] = []
        self.index = None
        self._load_or_build()

    # ── Embedding ─────────────────────────────────────────────────────────────

    def _embed(self, texts: List[str]) -> np.ndarray:
        resp = self.client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return np.array([e.embedding for e in resp.data], dtype=np.float32)

    # ── Index build / load ────────────────────────────────────────────────────

    def _load_or_build(self):
        index_file  = INDEX_DIR / "index.faiss"
        chunks_file = INDEX_DIR / "chunks.json"

        if index_file.exists() and chunks_file.exists():
            self._load(index_file, chunks_file)
        else:
            self._build(index_file, chunks_file)

    def _load(self, index_file: Path, chunks_file: Path):
        import faiss
        print("[RAG] Loading cached FAISS index...")
        self.index  = faiss.read_index(str(index_file))
        self.chunks = json.loads(chunks_file.read_text())
        print(f"[RAG] Loaded {len(self.chunks)} chunks.")

    def _build(self, index_file: Path, chunks_file: Path):
        import faiss
        print("[RAG] Building FAISS index from knowledge base...")
        self.chunks = _load_knowledge_base()
        print(f"[RAG] {len(self.chunks)} chunks loaded. Embedding...")

        # Embed in batches of 100
        all_embeddings = []
        batch_size = 100
        for i in range(0, len(self.chunks), batch_size):
            batch = self.chunks[i : i + batch_size]
            all_embeddings.append(self._embed(batch))
            print(f"[RAG] Embedded {min(i + batch_size, len(self.chunks))}/{len(self.chunks)}")

        matrix = np.vstack(all_embeddings)
        dim    = matrix.shape[1]

        self.index = faiss.IndexFlatIP(dim)   # inner-product (cosine after norm)
        faiss.normalize_L2(matrix)
        self.index.add(matrix)

        INDEX_DIR.mkdir(exist_ok=True)
        faiss.write_index(self.index, str(index_file))
        chunks_file.write_text(json.dumps(self.chunks, ensure_ascii=False))
        print(f"[RAG] Index saved to {INDEX_DIR}")

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str, k: int = 3) -> str:
        """Return top-k relevant knowledge base chunks for a query."""
        import faiss
        q = self._embed([query])
        faiss.normalize_L2(q)
        _, indices = self.index.search(q, k)
        results = [
            self.chunks[i]
            for i in indices[0]
            if 0 <= i < len(self.chunks)
        ]
        return "\n\n---\n\n".join(results)


# ── Singleton ─────────────────────────────────────────────────────────────────

_retriever: Optional[RAGRetriever] = None


def get_retriever(api_key: str = None) -> RAGRetriever:
    """Return the shared RAGRetriever instance (built once, reused)."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever(api_key=api_key)
    return _retriever
