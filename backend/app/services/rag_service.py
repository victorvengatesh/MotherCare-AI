"""
RAG Service — ChromaDB-backed retrieval for medical knowledge and patient history.
Includes secure PDF validations, page-level chunking, and SQL active document filtering.
"""
import os
import magic
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.db import models

logger = logging.getLogger("rag-service")

# ChromaDB lazy init
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


# ── PDF Validation ────────────────────────────────────────────────────────────

def validate_guideline_pdf(file_path: Path) -> Tuple[bool, str]:
    """
    Rigorously validates a guideline PDF file:
      - File size check (max 10MB)
      - Extension and MIME type check
      - Magic bytes check
      - Empty / Corrupted check
      - Encryption check
    """
    # Size check
    if not file_path.exists() or file_path.stat().st_size == 0:
        return False, "File is empty or does not exist."
    if file_path.stat().st_size > 10 * 1024 * 1024:
        return False, "File exceeds maximum allowed size (10 MB)."

    # Extension check
    if file_path.suffix.lower() != ".pdf":
        return False, "Invalid file extension. Expected a PDF file."

    # MIME & Magic bytes check
    try:
        mime = magic.from_file(str(file_path), mime=True)
        if mime != "application/pdf":
            return False, f"Invalid MIME type: {mime}. Expected application/pdf."
            
        with open(file_path, "rb") as f:
            header = f.read(4)
            if header != b"%PDF":
                return False, "Invalid magic bytes. Not a valid PDF document."
    except Exception as e:
        return False, f"Failed file type analysis: {str(e)}"

    # PDF integrity check using PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(str(file_path))
        if doc.is_encrypted:
            return False, "Encryption detected. Encrypted PDFs are not supported."
        if len(doc) == 0:
            return False, "The PDF has zero pages."
        doc.close()
    except Exception as e:
        return False, f"Corrupted or invalid PDF structure: {str(e)}"

    return True, "PDF successfully validated."


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


# ── Ingestion and Chunking ───────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Splits text into overlapping chunks for better semantic coverage."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def index_patient_data(text: str, user_id: str, filename: str = "report") -> int:
    """Chunks and stores a patient's health document in patient_history (Chroma)."""
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
    logger.info("Indexed %d chunks for patient %s", len(chunks), user_id)
    return len(chunks)

def index_medical_document_page_by_page(
    file_path: Path, 
    doc_id: str, 
    doc_title: str, 
    doc_version: str
) -> int:
    """
    Reads a validated PDF and indexes its text page-by-page with page-level citations in Chroma.
    """
    medical_col, _ = _get_collections()
    if medical_col is None:
        return 0

    import fitz
    doc = fitz.open(str(file_path))
    total_chunks = 0
    
    ids, docs, metas = [], [], []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if not text.strip():
            continue
            
        page_chunks = _chunk_text(text, chunk_size=600, overlap=100)
        for idx, chunk in enumerate(page_chunks):
            chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
            chunk_id = f"chunk_{doc_id}_p{page_num}_{chunk_hash}_{idx}"
            
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append({
                "doc_id": doc_id,
                "title": doc_title,
                "version": doc_version,
                "page": page_num + 1,  # 1-indexed for citation
                "source": doc_title
            })
            total_chunks += 1

    if ids:
        medical_col.upsert(documents=docs, metadatas=metas, ids=ids)
        
    doc.close()
    logger.info("Indexed %d chunks across %d pages for document ID %s", total_chunks, len(doc), doc_id)
    return total_chunks


# ── Safe Deletion ────────────────────────────────────────────────────────────

def delete_medical_chunks(doc_id: str) -> bool:
    """Removes all indexed chunks for a specific document from Chroma."""
    medical_col, _ = _get_collections()
    if medical_col is None:
        return False
    try:
        medical_col.delete(where={"doc_id": doc_id})
        logger.info("Deleted Chroma chunks for document ID: %s", doc_id)
        return True
    except Exception as e:
        logger.error("Failed to delete chunks: %s", e)
        return False


# ── Retrieval and Citation ────────────────────────────────────────────────────

def get_relevant_context(
    db: Session, 
    query: str, 
    user_id: str, 
    n_results: int = 3
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Retrieves semantic context with page-level citations.
    Only queries guidelines that are currently marked active/approved in SQLite database.
    
    Returns:
      (context_string, citations_list)
      If no active context is found, returns ("insufficient approved information", [])
    """
    medical_col, patient_col = _get_collections()
    context_parts = []
    citations = []

    # 1. Retrieve active guideline IDs from SQLite
    active_docs = db.query(models.RAGDocument).filter_by(is_active=True).all()
    active_doc_ids = [d.id for d in active_docs]

    # 2. Search medical knowledge base (only active docs)
    if medical_col is not None and active_doc_ids:
        try:
            # Query Chroma with active docs filter
            results = medical_col.query(
                query_texts=[query],
                n_results=max(n_results, 5),
                where={"doc_id": {"$in": active_doc_ids}}
            )
            
            if results["documents"] and results["documents"][0]:
                distances = results.get("distances", [[0.0] * len(results["documents"][0])])[0]
                zipped = list(zip(results["documents"][0], results["metadatas"][0], distances))
                
                # Sort by distance (smaller distance = better match)
                zipped.sort(key=lambda x: x[2])
                
                # Exclude poor-match noise (distance >= 1.3 is highly unrelated)
                filtered_zipped = [item for item in zipped if item[2] < 1.3]
                
                # Deduplicate very similar text fragments
                seen_texts = set()
                deduped = []
                for doc_text, meta, dist in filtered_zipped:
                    norm_text = " ".join(doc_text.lower().split())[:150]
                    if norm_text not in seen_texts:
                        seen_texts.add(norm_text)
                        deduped.append((doc_text, meta, dist))
                
                if deduped:
                    context_parts.append("--- Approved Clinical Guideline Context ---")
                    for doc_text, metadata, dist in deduped[:n_results]:
                        page = metadata.get("page", "?")
                        title = metadata.get("title", "Clinical Document")
                        version = metadata.get("version", "1.0")
                        
                        context_parts.append(f"[Source: {title} v{version}, Page {page} (match: {1.0 - min(dist, 1.0):.2f})]\n{doc_text}")
                        citations.append({
                            "title": title,
                            "version": version,
                            "page": page,
                            "text_snippet": doc_text[:120] + "..."
                        })
        except Exception as e:
            logger.warning("Medical RAG query failed: %s", e)
    
    # 3. Search patient's own records
    if patient_col is not None:
        try:
            results = patient_col.query(
                query_texts=[query],
                n_results=min(n_results, 2),
                where={"user_id": user_id},
            )
            if results["documents"] and results["documents"][0]:
                context_parts.append("--- Patient Medical Record History ---")
                for doc_text in results["documents"][0]:
                    context_parts.append(doc_text)
        except Exception as e:
            logger.warning("Patient RAG query failed: %s", e)

    # If no approved clinical evidence is fetched, we return fallback message
    if not citations and not context_parts:
        return "insufficient approved information", []
        
    return "\n\n".join(context_parts), citations
