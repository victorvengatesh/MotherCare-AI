"""
RAG Service — ChromaDB-backed retrieval for medical knowledge and patient history.

Collections:
  - medical_knowledge : WHO/UNICEF guidelines and static PDFs
  - patient_history   : Per-user uploaded health reports (filtered by user_id)
"""
import hashlib
import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger("rag-service")

# ── ChromaDB lazy init ────────────────────────────────────────────────────────
_chroma_client = None
_medical_col   = None
_patient_col   = None

CHROMA_DB_PATH = Path(__file__).resolve().parent.parent.parent / "chroma_db"


def _get_collections():
    global _chroma_client, _medical_col, _patient_col
    if _chroma_client is not None:
        return _medical_col, _patient_col
    try:
        import chromadb
        from chromadb.utils import embedding_functions

        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        _medical_col = _chroma_client.get_or_create_collection(
            name="medical_knowledge", embedding_function=ef
        )
        _patient_col = _chroma_client.get_or_create_collection(
            name="patient_history", embedding_function=ef
        )
        logger.info("ChromaDB initialised at %s", CHROMA_DB_PATH)
    except Exception as e:
        logger.error("ChromaDB init failed: %s", e)
    return _medical_col, _patient_col


# ── PDF Processing ────────────────────────────────────────────────────────────

async def process_pdf(file) -> str:
    """Reads an uploaded PDF and extracts all text with PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        raw = await file.read()
        doc = fitz.open(stream=raw, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        logger.info("PDF extracted: %d chars", len(text))
        return text
    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        return ""


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Splits long text into overlapping chunks for better retrieval."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# ── Indexing ──────────────────────────────────────────────────────────────────

def index_patient_data(text: str, user_id: str, filename: str = "report") -> int:
    """Chunks and stores a patient's health document in ChromaDB."""
    _, patient_col = _get_collections()
    if patient_col is None:
        return 0

    chunks = _chunk_text(text)
    ids, docs, metas = [], [], []
    for i, chunk in enumerate(chunks):
        doc_id = f"u_{user_id}_{hashlib.md5(chunk.encode()).hexdigest()}_{i}"
        ids.append(doc_id)
        docs.append(chunk)
        metas.append({"user_id": user_id, "filename": filename, "chunk": i})

    patient_col.upsert(documents=docs, metadatas=metas, ids=ids)
    logger.info("Indexed %d chunks for user %s", len(chunks), user_id)
    return len(chunks)


def index_medical_document(text: str, doc_name: str) -> int:
    """Indexes a static medical/clinical document (admin use)."""
    medical_col, _ = _get_collections()
    if medical_col is None:
        return 0

    chunks = _chunk_text(text)
    ids, docs, metas = [], [], []
    for i, chunk in enumerate(chunks):
        doc_id = f"med_{doc_name}_{i}"
        ids.append(doc_id)
        docs.append(chunk)
        metas.append({"source": doc_name, "chunk": i})

    medical_col.upsert(documents=docs, metadatas=metas, ids=ids)
    return len(chunks)


# ── Retrieval ─────────────────────────────────────────────────────────────────

def get_relevant_context(query: str, user_id: str, n_results: int = 3) -> str:
    """
    Retrieves the most relevant context for a query from:
    1. The patient's own indexed documents
    2. General medical knowledge base
    """
    medical_col, patient_col = _get_collections()
    context_parts = []

    # Search patient's own records
    if patient_col is not None:
        try:
            results = patient_col.query(
                query_texts=[query],
                n_results=min(n_results, 2),
                where={"user_id": user_id},
            )
            if results["documents"] and results["documents"][0]:
                context_parts.append("--- From Your Health Records ---")
                context_parts.extend(results["documents"][0])
        except Exception as e:
            logger.warning("Patient RAG query failed: %s", e)

    # Search medical knowledge base
    if medical_col is not None:
        try:
            count = medical_col.count()
            if count > 0:
                results = medical_col.query(
                    query_texts=[query],
                    n_results=min(n_results, 2),
                )
                if results["documents"] and results["documents"][0]:
                    context_parts.append("--- From Clinical Guidelines ---")
                    context_parts.extend(results["documents"][0])
        except Exception as e:
            logger.warning("Medical RAG query failed: %s", e)

    return "\n\n".join(context_parts) if context_parts else ""
