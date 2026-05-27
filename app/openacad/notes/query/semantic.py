"""In-memory atom + chunk embeddings, persisted as numpy compressed arrays.

The embedding model is lazy-loaded on first use to keep boot fast. Cosine
search is a single matrix-vector multiply — trivially fast at vault sizes
we care about (<=100K atoms).

Persistence uses np.savez_compressed → atoms.npz / chunks.npz, with two named
arrays: `ids` (string) and `vectors` (float32 [N, 384]). Both dtypes are
non-object, so numpy never invokes any unsafe deserialization path on load.
"""

from pathlib import Path
from threading import Lock

import numpy as np

from openacad.runtime.settings import settings

_model = None
_model_lock = Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                # Lazy import — sentence_transformers is heavy.
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """Return a (N, 384) float32 matrix of L2-normalized embeddings."""
    if not texts:
        return np.zeros((0, 384), dtype="float32")
    model = _get_model()
    vecs = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return vecs.astype("float32")


class EmbeddingStore:
    """A persistent {id: vector} store backed by .npz (str + float32 only)."""

    DIM = 384  # MiniLM-L6-v2

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ids: np.ndarray = np.array([], dtype="<U128")
        self._vectors: np.ndarray = np.zeros((0, self.DIM), dtype="float32")
        self.load()

    def load(self) -> None:
        if self.path.exists():
            data = np.load(self.path)
            self._ids = data["ids"]
            self._vectors = data["vectors"].astype("float32")

    def save(self) -> None:
        np.savez_compressed(self.path, ids=self._ids, vectors=self._vectors)

    def __len__(self) -> int:
        return int(self._ids.shape[0])

    def upsert_many(self, items: list[tuple[str, str]]) -> None:
        """items is a list of (id, text)."""
        if not items:
            return
        new_ids = [i for i, _ in items]
        texts = [t for _, t in items]
        new_vecs = embed(texts)

        # Drop any existing entries that we're about to re-insert (re-embed semantics).
        if len(self._ids):
            keep = np.array([i not in set(new_ids) for i in self._ids.tolist()], dtype=bool)
            self._ids = self._ids[keep]
            self._vectors = self._vectors[keep]

        self._ids = np.concatenate([self._ids, np.array(new_ids, dtype="<U128")])
        self._vectors = (
            np.vstack([self._vectors, new_vecs]) if self._vectors.size else new_vecs
        )
        self.save()

    def upsert(self, id: str, text: str) -> None:
        self.upsert_many([(id, text)])

    def remove(self, id: str) -> None:
        idx = np.where(self._ids == id)[0]
        if len(idx) == 0:
            return
        self._ids = np.delete(self._ids, idx[0])
        self._vectors = np.delete(self._vectors, idx[0], axis=0)
        self.save()

    def search(self, query: str, limit: int = 10) -> list[tuple[str, float]]:
        if len(self) == 0:
            return []
        qvec = embed([query])[0]
        # Both vectors and qvec are L2-normalized → dot product == cosine.
        scores = self._vectors @ qvec
        order = np.argsort(-scores)[:limit]
        return [(str(self._ids[i]), float(scores[i])) for i in order]


# ── scenario-aware stores ───────────────────────────────────────────────


# atoms.npz is per-scenario (Curated, Drafted, Evolving each grow their own set).
# chunks.npz is shared (every scenario can see the same chunk embeddings).
_atoms_stores: dict[str, EmbeddingStore] = {}
_chunks_store: EmbeddingStore | None = None


def atoms_store() -> EmbeddingStore:
    """Atom embedding store for the active scenario."""
    from openacad.runtime.scenario import active_scenario
    key = active_scenario().key
    store = _atoms_stores.get(key)
    if store is None:
        store = EmbeddingStore(active_scenario().atoms_npz_path)
        _atoms_stores[key] = store
    return store


def chunks_store() -> EmbeddingStore:
    """Chunk embedding store — shared across all scenarios."""
    from openacad.runtime.scenario import shared_chunks_npz_path
    global _chunks_store
    if _chunks_store is None:
        _chunks_store = EmbeddingStore(shared_chunks_npz_path())
    return _chunks_store
