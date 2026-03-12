import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseDocumentStore(ABC):
    """
    Abstract vector store interface for RAG.
    Implementations can wrap ChromaDB, FAISS, pgvector, Qdrant, etc.
    """

    @abstractmethod
    def add_documents(self, documents, metadatas=None):
        """
        Index a batch of text documents.

        Args:
            documents: list of str – text chunks to store
            metadatas: optional list of dict – metadata per document

        Returns:
            list of str – assigned document IDs
        """

    @abstractmethod
    def search(self, query, top_k=5, filters=None):
        """
        Retrieve the most relevant documents for a query.

        Args:
            query: str – the search query (will be embedded internally)
            top_k: number of results to return
            filters: optional dict – metadata filters

        Returns:
            list of dict with keys: "content", "metadata", "score"
        """

    @abstractmethod
    def delete_documents(self, document_ids):
        """Remove documents by their IDs."""


class ChromaDocumentStore(BaseDocumentStore):
    """
    ChromaDB-backed vector store.
    Activate by installing `chromadb` and setting AI_VECTOR_STORE=chroma.
    """

    def __init__(self, collection_name='memo_rag', persist_directory=None):
        try:
            import chromadb
        except ImportError:
            raise RuntimeError(
                'chromadb is not installed. Run: pip install chromadb'
            )

        if persist_directory:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.Client()

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={'hnsw:space': 'cosine'},
        )

    def add_documents(self, documents, metadatas=None):
        import uuid
        ids = [str(uuid.uuid4()) for _ in documents]
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        return ids

    def search(self, query, top_k=5, filters=None):
        query_params = {
            'query_texts': [query],
            'n_results': top_k,
        }
        if filters:
            query_params['where'] = filters

        results = self.collection.query(**query_params)

        hits = []
        for i, doc in enumerate(results['documents'][0]):
            hits.append({
                'content': doc,
                'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                'score': results['distances'][0][i] if results.get('distances') else 0.0,
            })
        return hits

    def delete_documents(self, document_ids):
        self.collection.delete(ids=document_ids)
