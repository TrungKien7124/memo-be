import logging
from abc import ABC, abstractmethod
import requests

logger = logging.getLogger(__name__)


class BaseDocumentStore(ABC):
    """
    Interface trừu tượng cho vector store dùng trong RAG.

    Mục đích:
        Chuẩn hóa contract cho các backend lưu trữ vector như Chroma, FAISS,
        pgvector hoặc Qdrant để phần retrieval phía trên không phụ thuộc
        implementation cụ thể.
    """

    @abstractmethod
    def add_documents(self, documents, metadatas=None):
        """
        Thêm một lô tài liệu văn bản vào vector store.

        Args:
            documents: Danh sách text chunk cần index.
            metadatas: Danh sách metadata tương ứng cho từng document. Có thể
                là ``None`` nếu không cần metadata.

        Returns:
            Danh sách document id được gán trong vector store.

        Raises:
            NotImplementedError: Hàm bắt buộc phải được class con triển khai.
        """

    @abstractmethod
    def search(self, query, top_k=5, filters=None):
        """
        Truy vấn các document liên quan nhất cho một câu hỏi.

        Args:
            query: Câu truy vấn gốc của người dùng.
            top_k: Số lượng kết quả tối đa cần trả về.
            filters: Bộ lọc metadata tùy chọn để giới hạn tập document.

        Returns:
            Danh sách dict có các key như ``content``, ``metadata`` và
            ``score``.

        Raises:
            NotImplementedError: Hàm bắt buộc phải được class con triển khai.
        """

    @abstractmethod
    def delete_documents(self, document_ids):
        """
        Xóa document theo danh sách id khỏi vector store.

        Args:
            document_ids: Danh sách id document cần xóa.

        Returns:
            Không trả về giá trị.

        Raises:
            NotImplementedError: Hàm bắt buộc phải được class con triển khai.
        """


class ChromaDocumentStore(BaseDocumentStore):
    """
    Vector store triển khai trên ChromaDB.

    Mục đích:
        Cung cấp implementation thật cho contract ``BaseDocumentStore`` bằng
        Chroma và embedding từ Ollama.
    """

    class OllamaEmbeddingFunction:
        """Adapter giúp Chroma gọi Ollama embedding API theo đúng interface."""

        def __init__(self, url: str, model: str, timeout: int = 30):
            """
            Khởi tạo embedding function cho Ollama.

            Args:
                url: Base URL của Ollama embedding endpoint.
                model: Tên model embedding cần gọi.
                timeout: Timeout request tính theo giây.

            Returns:
                Không trả về giá trị.

            Raises:
                Không chủ động raise exception tại thời điểm khởi tạo.
            """
            self.url = url.rstrip('/')
            self.model = model
            self.timeout = timeout

        def __call__(self, input_texts):
            """
            Sinh embedding cho một hoặc nhiều đoạn text.

            Args:
                input_texts: Một chuỗi đơn hoặc danh sách chuỗi cần embed.

            Returns:
                Danh sách vector embedding theo thứ tự đầu vào.

            Raises:
                requests.HTTPError: Khi Ollama API trả về HTTP status lỗi.
                RuntimeError: Khi Ollama trả về payload không có embedding.
            """
            if isinstance(input_texts, str):
                input_texts = [input_texts]
            if input_texts is None:
                input_texts = []
            embeddings = []
            for text in input_texts:
                response = requests.post(
                    f'{self.url}/api/embeddings',
                    json={
                        'model': self.model,
                        'prompt': text,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                embedding = payload.get('embedding')
                if not embedding:
                    raise RuntimeError('Ollama embedding API returned empty embedding.')
                embeddings.append(embedding)
            return embeddings

    def __init__(
        self,
        collection_name='memo_rag',
        persist_directory=None,
        embedding_url='http://host.docker.internal:11434',
        embedding_model='nomic-embed-text',
        embedding_timeout=30,
    ):
        """
        Khởi tạo Chroma client và collection dùng cho RAG.

        Args:
            collection_name: Tên collection sẽ dùng trong Chroma.
            persist_directory: Đường dẫn lưu persistent store. Nếu ``None`` thì
                dùng client in-memory/local mặc định của Chroma.
            embedding_url: URL của Ollama embedding service.
            embedding_model: Tên model embedding dùng để index/query.
            embedding_timeout: Timeout request embedding theo giây.

        Returns:
            Không trả về giá trị.

        Raises:
            RuntimeError: Khi package ``chromadb`` chưa được cài trong môi
                trường chạy.
        """
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

        embedding_function = self.OllamaEmbeddingFunction(
            url=embedding_url,
            model=embedding_model,
            timeout=embedding_timeout,
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={'hnsw:space': 'cosine'},
            embedding_function=embedding_function,
        )

    def add_documents(self, documents, metadatas=None):
        """
        Thêm batch document mới vào collection Chroma hiện tại.

        Args:
            documents: Danh sách text chunk cần index.
            metadatas: Metadata tương ứng cho từng chunk.

        Returns:
            Danh sách UUID string được tạo cho các document vừa thêm.

        Raises:
            Exception: Các lỗi từ Chroma khi add document không hợp lệ hoặc
                vector store không sẵn sàng.
        """
        import uuid
        ids = [str(uuid.uuid4()) for _ in documents]
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        return ids

    def search(self, query, top_k=5, filters=None):
        """
        Truy vấn collection Chroma và chuẩn hóa kết quả về dạng hit list.

        Args:
            query: Nội dung query text cần tìm context.
            top_k: Số lượng kết quả tối đa cần lấy.
            filters: Metadata filter gửi xuống Chroma ``where`` clause.

        Returns:
            Danh sách hit dict gồm nội dung, metadata và score/distance.

        Raises:
            Exception: Các lỗi từ Chroma query hoặc embedding/query pipeline.
        """
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
        """
        Xóa document khỏi collection Chroma theo danh sách id.

        Args:
            document_ids: Danh sách id document đã lưu trong Chroma.

        Returns:
            Không trả về giá trị.

        Raises:
            Exception: Các lỗi từ Chroma khi xóa document thất bại.
        """
        self.collection.delete(ids=document_ids)
