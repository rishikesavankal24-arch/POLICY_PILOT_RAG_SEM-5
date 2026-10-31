# pyrefly: ignore [missing-import]
from sentence_transformers import SentenceTransformer

from app.services.rag.config.settings import EMBEDDING_MODEL_NAME, EMBEDDING_DIM

# ---------------------------------------------------------------------------
# Process-level singleton.  The SentenceTransformer is expensive to load
# (~300 ms for all-MiniLM-L6-v2) and is safe to share across threads for
# inference.  We initialise it once and reuse across all PolicyEmbedder
# instances so that customer requests pay the load cost at most once.
# ---------------------------------------------------------------------------
_shared_model: SentenceTransformer | None = None


def _get_shared_model() -> SentenceTransformer:
    global _shared_model
    if _shared_model is None:
        _shared_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _shared_model


class PolicyEmbedder:
    """Generate embeddings for policy text using the project's canonical model.

    The canonical model is ``sentence-transformers/all-MiniLM-L6-v2``, which
    produces ``EMBEDDING_DIM`` (384)-dimensional vectors.  The ``Vector(384)``
    column in ``policy_chunks`` must stay in sync with this dimension.  See
    ``app/services/rag/config/settings.py`` for the authoritative constants.
    """

    def __init__(self) -> None:
        self.model = _get_shared_model()

    def embed_text(self, text: str) -> list[float]:
        """Generate one embedding vector for a single text."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        if not text.strip():
            raise ValueError("text must not be empty")

        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""
        if not isinstance(texts, list):
            raise TypeError("texts must be a list")

        if not texts:
            raise ValueError("texts must not be empty")

        if any(not isinstance(text, str) for text in texts):
            raise TypeError("every item in texts must be a string")

        if any(not text.strip() for text in texts):
            raise ValueError("texts must not contain empty strings")

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embeddings.tolist()