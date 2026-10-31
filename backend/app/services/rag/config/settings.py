import os

# ---------------------------------------------------------------------------
# Embedding model
# ---------------------------------------------------------------------------
# EMBEDDING_MODEL_NAME must remain consistent with the pgvector column
# dimension (Vector(384)) declared in PolicyChunk.  The default model
# sentence-transformers/all-MiniLM-L6-v2 produces exactly 384-dimensional
# embeddings.  If you change this value you MUST also run an Alembic migration
# to update the Vector column dimension and re-index all policy chunks.
EMBEDDING_MODEL_NAME = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Dimension of the embedding vector produced by EMBEDDING_MODEL_NAME.
# Keep this in sync with the Vector(N) column definition in models.py.
EMBEDDING_DIM = 384

# ---------------------------------------------------------------------------
# Retrieval tuning
# ---------------------------------------------------------------------------
DEFAULT_TOP_K = int(os.getenv("RAG_DEFAULT_TOP_K", "5"))
SECOND_TOP_K = int(os.getenv("RAG_SECOND_TOP_K", "20"))
MAX_RETRIEVAL_ATTEMPTS = 2
