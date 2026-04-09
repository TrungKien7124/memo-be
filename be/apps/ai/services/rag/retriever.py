import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_document_store_instance = None


def reset_document_store_cache():
    global _document_store_instance
    _document_store_instance = None


def get_document_store():
    """
    Lấy singleton document store theo cấu hình RAG hiện tại.

    Args:
        Không có tham số.

    Returns:
        Instance của document store đã cấu hình, hoặc ``None`` nếu RAG đang
        tắt hay backend không hợp lệ.

    Raises:
        Exception: Có thể phát sinh từ constructor của backend vector store,
            ví dụ thiếu dependency hoặc lỗi kết nối khởi tạo.
    """
    global _document_store_instance

    if not getattr(settings, 'AI_RAG_ENABLED', False):
        return None

    if _document_store_instance is not None:
        return _document_store_instance

    store_backend = getattr(settings, 'AI_VECTOR_STORE', 'pgvector')
    persist_dir = getattr(settings, 'AI_VECTOR_STORE_PATH', None)

    if store_backend == 'pgvector':
        from apps.ai.services.rag.document_store import PgVectorDocumentStore

        _document_store_instance = PgVectorDocumentStore()
    elif store_backend == 'chroma':
        from apps.ai.services.rag.document_store import ChromaDocumentStore

        _document_store_instance = ChromaDocumentStore(
            collection_name=getattr(settings, 'AI_VECTOR_COLLECTION', 'memo_rag'),
            persist_directory=persist_dir,
            embedding_url=getattr(settings, 'AI_OLLAMA_EMBED_URL', 'http://host.docker.internal:11434'),
            embedding_model=getattr(settings, 'AI_OLLAMA_EMBED_MODEL', 'nomic-embed-text'),
            embedding_timeout=getattr(settings, 'AI_OLLAMA_EMBED_TIMEOUT', 30),
        )
    else:
        logger.warning('Unknown vector store backend: %s – RAG disabled', store_backend)
        return None

    return _document_store_instance


def retrieve_context(query, top_k=None, filters=None):
    """
    Truy xuất các chunk context liên quan nhất cho câu hỏi đầu vào.

    Args:
        query: Câu hỏi hoặc tin nhắn đầu vào của người dùng.
        top_k: Số lượng chunk tối đa cần lấy. Nếu ``None`` sẽ lấy từ settings.
        filters: Metadata filter tùy chọn, ví dụ theo ``lesson_id``.

    Returns:
        Danh sách nội dung text chunk. Nếu retrieval lỗi hoặc RAG tắt thì trả
        về danh sách rỗng.

    Raises:
        Không chủ động raise exception. Hàm tự log lỗi và trả ``[]`` khi
        retrieval thất bại.
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
    Index một batch document vào vector store phục vụ RAG.

    Args:
        documents: Danh sách text chunk cần index.
        metadatas: Danh sách metadata đi kèm cho từng chunk.

    Returns:
        Danh sách document id mới tạo. Nếu RAG tắt hoặc index lỗi thì trả
        ``[]``.

    Raises:
        Không chủ động raise exception. Hàm tự log lỗi và trả ``[]`` khi index
        thất bại.
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


def delete_documents(document_ids):
    """
    Xóa các document đã index khỏi vector store.

    Args:
        document_ids: Danh sách id document cần xóa.

    Returns:
        ``True`` nếu không có gì cần xóa hoặc xóa thành công, ``False`` nếu
        RAG tắt hay xóa thất bại.

    Raises:
        Không chủ động raise exception. Hàm tự log lỗi và trả ``False`` khi
        xóa thất bại.
    """
    if not document_ids:
        return True

    store = get_document_store()
    if store is None:
        logger.info('RAG is disabled, skipping document deletion')
        return False

    try:
        store.delete_documents(document_ids=document_ids)
        return True
    except Exception as exc:
        logger.error('RAG deletion failed: %s', exc)
        return False
