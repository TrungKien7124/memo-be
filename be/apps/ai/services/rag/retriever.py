import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_document_store_instance = None


def get_document_store():
    """
    Singleton factory for the configured vector store.
    Returns None if RAG is not enabled.
    """
    global _document_store_instance

    if not getattr(settings, 'AI_RAG_ENABLED', False):
        return None

    if _document_store_instance is not None:
        return _document_store_instance

    store_backend = getattr(settings, 'AI_VECTOR_STORE', 'chroma')
    persist_dir = getattr(settings, 'AI_VECTOR_STORE_PATH', None)

    if store_backend == 'chroma':
        from apps.ai.services.rag.document_store import ChromaDocumentStore
        _document_store_instance = ChromaDocumentStore(
            collection_name=getattr(settings, 'AI_VECTOR_COLLECTION', 'memo_rag'),
            persist_directory=persist_dir,
        )
    else:
        logger.warning('Unknown vector store backend: %s – RAG disabled', store_backend)
        return None

    return _document_store_instance


def retrieve_context(query, top_k=None, filters=None):
    """
    Retrieve relevant document chunks for a query.
    Returns empty list if RAG is disabled or no store is configured.

    Args:
        query: str – the user's question or message
        top_k: int – how many chunks to retrieve (default from settings)
        filters: dict – optional metadata filters (e.g. {"course_id": "..."})

    Returns:
        list of str – relevant text chunks, ordered by relevance
    """
    store = get_document_store()
    if store is None:
        return []

    if top_k is None:
        top_k = getattr(settings, 'AI_RAG_TOP_K', 5)

    try:
        results = store.search(query=query, top_k=top_k, filters=filters)
        return [hit['content'] for hit in results]
    except Exception as exc:
        logger.error('RAG retrieval failed: %s', exc)
        return []


def index_documents(documents, metadatas=None):
    """
    Add documents to the vector store for RAG indexing.
    Useful for indexing course content, flashcard decks, etc.

    Args:
        documents: list of str – text chunks
        metadatas: list of dict – metadata per chunk

    Returns:
        list of str – document IDs, or empty list if RAG is disabled.
    """
    store = get_document_store()
    if store is None:
        logger.info('RAG is disabled, skipping document indexing')
        return []

    try:
        return store.add_documents(documents, metadatas=metadatas)
    except Exception as exc:
        logger.error('RAG indexing failed: %s', exc)
        return []
