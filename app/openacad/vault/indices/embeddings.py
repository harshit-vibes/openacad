"""MiniLM embeddings persisted to ``.openacad/index/embeddings.npz``.

The model is loaded lazily — instantiating ``EmbeddingIndex`` does not
download or import the encoder, so tests that exercise the *index*
(add/remove/persist) without semantic search are cheap. The encoder is
only loaded when :meth:`search` or :meth:`add` is called with a real
atom body.

Tests can inject a fake encoder (any callable that takes
``list[str] -> ndarray``) via the ``encoder=`` kwarg, or set
``OPENACAD_EMBEDDING_BACKEND=hash`` to use the deterministic hash
encoder (fast, no model download). The hash encoder is good enough for
sync-correctness tests but not for semantic relevance.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np

EMBEDDING_DIM = 384  # MiniLM-L6-v2 dim; hash encoder also produces this size
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


Encoder = Callable[[Sequence[str]], np.ndarray]


def _hash_encode(texts: Sequence[str]) -> np.ndarray:
    """Deterministic, model-free encoder for tests + offline use.

    Produces L2-normalised vectors that are stable across runs and OS.
    Quality is poor (it's just folded SHA1 bytes) but identity / order
    invariants hold.
    """
    out = np.zeros((len(texts), EMBEDDING_DIM), dtype=np.float32)
    for i, text in enumerate(texts):
        vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        for salt in (b"a", b"b", b"c", b"d"):
            digest = hashlib.sha1(salt + text.encode("utf-8")).digest()
            arr = np.frombuffer(digest * (EMBEDDING_DIM // len(digest) + 1), dtype=np.uint8)
            vec += arr[:EMBEDDING_DIM].astype(np.float32) / 255.0
        vec -= vec.mean()
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        out[i] = vec
    return out


def _load_sentence_transformer_encoder(model_name: str) -> Encoder:
    """Build an encoder backed by sentence-transformers (lazy)."""
    from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

    model = SentenceTransformer(model_name)

    def encode(texts: Sequence[str]) -> np.ndarray:
        arr = model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return np.asarray(arr, dtype=np.float32)

    return encode


def _default_encoder() -> Encoder:
    backend = os.environ.get("OPENACAD_EMBEDDING_BACKEND", "").lower()
    if backend == "hash":
        return _hash_encode
    try:
        return _load_sentence_transformer_encoder(DEFAULT_MODEL)
    except Exception:
        return _hash_encode


class EmbeddingIndex:
    """In-memory cosine search over atom embeddings, persisted to ``.npz``.

    The on-disk format is a numpy ``.npz`` archive of two arrays: ``ids``
    (string array of atom ids) and ``vectors`` (float32 matrix). We
    deliberately do NOT use object pickling — the file is loaded with
    ``allow_pickle=False`` to keep it safe to share between users.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        encoder: Encoder | None = None,
        dim: int = EMBEDDING_DIM,
    ) -> None:
        self.path = Path(path)
        self.dim = dim
        self._encoder: Encoder | None = encoder
        # parallel arrays — atom id at index i ↔ self._vectors[i]
        self._ids: list[str] = []
        self._vectors: np.ndarray = np.zeros((0, dim), dtype=np.float32)
        self._id_to_index: dict[str, int] = {}
        self._load()

    # ------------------------------------------------------------------
    # disk I/O
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.path.exists():
            return
        # ids are stored as a fixed-width unicode array to avoid pickle.
        with np.load(self.path) as data:
            self._ids = [str(s) for s in data["ids"].tolist()]
            self._vectors = data["vectors"].astype(np.float32)
        self._id_to_index = {aid: i for i, aid in enumerate(self._ids)}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # np.savez appends ``.npz`` to the path if it isn't there. We
        # write to a sibling ``.tmp.npz`` file then atomically replace.
        tmp = self.path.with_name(self.path.name + ".tmp.npz")
        # Use a unicode dtype rather than object — keeps the npz
        # pickle-free and portable.
        ids_arr = np.asarray(self._ids, dtype=np.str_)
        # np.savez writes to <name>.npz; if our path already ends in
        # .npz we save directly to the tmp file (which also ends in
        # .npz so no auto-suffix is added).
        np.savez(str(tmp)[:-4], ids=ids_arr, vectors=self._vectors)
        tmp.replace(self.path)

    # ------------------------------------------------------------------
    # encoder (lazy)
    # ------------------------------------------------------------------

    @property
    def encoder(self) -> Encoder:
        if self._encoder is None:
            self._encoder = _default_encoder()
        return self._encoder

    # ------------------------------------------------------------------
    # mutation
    # ------------------------------------------------------------------

    def add(self, atom_id: str, text: str) -> None:
        """Add or replace the embedding for ``atom_id``."""
        vec = self.encoder([text])[0]
        if atom_id in self._id_to_index:
            idx = self._id_to_index[atom_id]
            self._vectors[idx] = vec
        else:
            self._id_to_index[atom_id] = len(self._ids)
            self._ids.append(atom_id)
            self._vectors = np.vstack([self._vectors, vec[None, :]])

    def remove(self, atom_id: str) -> None:
        idx = self._id_to_index.pop(atom_id, None)
        if idx is None:
            return
        self._ids.pop(idx)
        self._vectors = np.delete(self._vectors, idx, axis=0)
        self._id_to_index = {aid: i for i, aid in enumerate(self._ids)}

    def clear(self) -> None:
        self._ids = []
        self._vectors = np.zeros((0, self.dim), dtype=np.float32)
        self._id_to_index = {}

    # ------------------------------------------------------------------
    # query
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        if not self._ids:
            return []
        qvec = self.encoder([query])[0]
        scores = self._vectors @ qvec
        top_idx = np.argsort(-scores)[: max(1, top_k)]
        return [(self._ids[int(i)], float(scores[int(i)])) for i in top_idx]

    # ------------------------------------------------------------------
    # introspection
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._ids)

    def __contains__(self, atom_id: object) -> bool:
        return isinstance(atom_id, str) and atom_id in self._id_to_index

    @property
    def ids(self) -> list[str]:
        return list(self._ids)


__all__ = ["EmbeddingIndex"]
