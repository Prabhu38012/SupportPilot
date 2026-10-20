import hashlib
import math
import re
from pathlib import Path

import chromadb

from app.config import Settings
from app.schemas import Chunk

_STOP = set("a an the is are was were be to of in on for and or i my me you your do does can how what it this that with at by".split())


class Embedder:
    """'default' = Chroma's bundled MiniLM (needs a one-time model download).
    'hash' = tiny deterministic bag-of-words embedding for offline tests."""

    def __init__(self, kind: str):
        self.kind = kind
        self._default = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.kind == "hash":
            return [self._hash(t) for t in texts]
        if self._default is None:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            self._default = DefaultEmbeddingFunction()
        return [list(map(float, v)) for v in self._default(texts)]

    @staticmethod
    def _hash(text: str, dim: int = 4096) -> list[float]:
        vec = [0.0] * dim
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            if tok in _STOP:
                continue
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def chunk_markdown(path: Path, max_chars: int = 900) -> list[tuple[str, str]]:
    """Split a markdown doc into (heading, text) chunks on '## ' sections, then by paragraph."""
    text = path.read_text(encoding="utf-8")
    title = (re.search(r"^# (.+)$", text, flags=re.M) or [None, path.stem])[1]
    out: list[tuple[str, str]] = []
    for section in re.split(r"\n(?=## )", text):
        m = re.match(r"## (.+)", section)
        heading = m.group(1).strip() if m else title
        body = re.sub(r"^#{1,2} .+\n?", "", section, count=1).strip()
        if not body:
            continue
        buf = ""
        for para in body.split("\n\n"):
            if buf and len(buf) + len(para) > max_chars:
                out.append((heading, buf.strip()))
                buf = ""
            buf += para + "\n\n"
        if buf.strip():
            out.append((heading, buf.strip()))
    return out


class Retriever:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.embedder = Embedder(settings.embeddings)
        self.client = chromadb.PersistentClient(path=settings.chroma_dir)
        self.col = self.client.get_or_create_collection("support_kb", metadata={"hnsw:space": "cosine"})

    def count(self) -> int:
        return self.col.count()

    def ingest(self, kb_dir: str | None = None, reset: bool = True) -> int:
        kb = Path(kb_dir or self.settings.kb_dir)
        if reset:
            self.client.delete_collection("support_kb")
            self.col = self.client.get_or_create_collection("support_kb", metadata={"hnsw:space": "cosine"})
        ids, docs, metas = [], [], []
        for f in sorted(kb.glob("*.md")):
            for i, (heading, body) in enumerate(chunk_markdown(f)):
                ids.append(f"{f.name}#{i}")
                docs.append(f"{heading}\n{body}")
                metas.append({"source": f.name, "heading": heading})
        if ids:
            self.col.add(ids=ids, documents=docs, metadatas=metas, embeddings=self.embedder.embed(docs))
        return len(ids)

    def search(self, query: str, k: int | None = None) -> list[Chunk]:
        k = k or self.settings.top_k
        n = self.col.count()
        if n == 0:
            return []
        res = self.col.query(query_embeddings=self.embedder.embed([query]), n_results=min(k, n))
        chunks = []
        for cid, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]):
            chunks.append(Chunk(id=cid, source=meta["source"], heading=meta["heading"], text=doc, score=round(1 - dist, 4)))
        return chunks
