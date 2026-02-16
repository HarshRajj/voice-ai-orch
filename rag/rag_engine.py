"""RAG Engine using Pinecone for vector storage with Google Embeddings and Cerebras LLM."""

import os
import uuid
import json
import logging
from pathlib import Path
from typing import Optional

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
)
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.cerebras import Cerebras
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)

DOCS_METADATA_FILE = "docs_metadata.json"
METADATA_DIR = "./rag_metadata"


class RAGEngine:
    """RAG Engine with Pinecone vector store, Google embeddings, and Cerebras LLM."""

    def __init__(
        self,
        data_dir: str = "Data",
        prompt_file: str = "Prompt/prompt.md",
        index_name: str = "knowledge-base",
        embedding_model: str = "gemini-embedding-001",
        llm_model: str = "llama-3.3-70b",
        dimension: int = 3072,
    ):
        self.data_dir = Path(data_dir)
        self.prompt_file = Path(prompt_file)
        self.index_name = index_name
        self.dimension = dimension

        # Configure LlamaIndex with Google embeddings + Cerebras LLM
        Settings.embed_model = GoogleGenAIEmbedding(
            model_name=embedding_model,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
        Settings.llm = Cerebras(
            model=llm_model,
            api_key=os.getenv("CEREBRAS_API_KEY"),
        )
        Settings.node_parser = SemanticSplitterNodeParser(
            buffer_size=1,
            breakpoint_percentile_threshold=95,
            embed_model=Settings.embed_model,
        )

        self.index: Optional[VectorStoreIndex] = None
        self.query_engine = None
        self.system_prompt = self._load_system_prompt()
        self.docs_metadata = self._load_docs_metadata()

        # Initialize Pinecone
        self._init_pinecone()

    def _init_pinecone(self):
        """Initialize Pinecone client, create index if needed, and connect."""
        import time

        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY must be set in your .env file")

        self.pc = Pinecone(api_key=api_key)

        # Check if index exists and has correct dimensions
        existing_indexes = {idx.name: idx for idx in self.pc.list_indexes()}
        if self.index_name in existing_indexes:
            existing_dim = existing_indexes[self.index_name].dimension
            if existing_dim != self.dimension:
                logger.warning(
                    f"Pinecone index '{self.index_name}' has dimension {existing_dim}, "
                    f"expected {self.dimension}. Deleting and recreating..."
                )
                self.pc.delete_index(self.index_name)
                # Wait for deletion to propagate
                logger.info("Waiting for index deletion to propagate...")
                time.sleep(10)
                existing_indexes = {idx.name: idx for idx in self.pc.list_indexes()}

        # Create index if it doesn't exist
        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name} (dim={self.dimension})")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            # Wait for index to be ready
            logger.info("Waiting for Pinecone index to be ready...")
            for _ in range(12):  # up to 60s
                try:
                    desc = self.pc.describe_index(self.index_name)
                    if desc.status.get("ready", False):
                        break
                except Exception:
                    pass
                time.sleep(5)
            logger.info(f"Pinecone index '{self.index_name}' created and ready")

        pinecone_index = self.pc.Index(self.index_name)
        self.vector_store = PineconeVectorStore(pinecone_index=pinecone_index)

        # Build LlamaIndex from existing Pinecone store
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)
        self._create_query_engine()
        logger.info(f"Connected to Pinecone index: {self.index_name}")

    def _create_query_engine(self):
        """Create query engine from current index."""
        if self.index:
            from llama_index.core.prompts import PromptTemplate

            # Strict synthesis prompt — prevents RAG LLM from hallucinating
            qa_prompt = PromptTemplate(
                "You are answering questions using ONLY the context below.\n"
                "Do NOT add any information that is not explicitly in the context.\n"
                "If the context does not contain the answer, say: 'This information is not available in the provided documents.'\n"
                "Be specific and quote details (names, numbers, titles) exactly as they appear.\n\n"
                "Context:\n{context_str}\n\n"
                "Question: {query_str}\n\n"
                "Answer:"
            )

            self.query_engine = self.index.as_query_engine(
                similarity_top_k=5,
                response_mode="compact",
                text_qa_template=qa_prompt,
            )

    def _load_system_prompt(self) -> str:
        """Load system prompt from file."""
        if self.prompt_file.exists():
            with open(self.prompt_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _load_docs_metadata(self) -> dict:
        """Load document metadata from JSON file."""
        Path(METADATA_DIR).mkdir(parents=True, exist_ok=True)
        meta_path = Path(METADATA_DIR) / DOCS_METADATA_FILE
        if meta_path.exists():
            with open(meta_path, "r") as f:
                return json.load(f)
        return {}

    def _save_docs_metadata(self):
        """Save document metadata to JSON file."""
        Path(METADATA_DIR).mkdir(parents=True, exist_ok=True)
        meta_path = Path(METADATA_DIR) / DOCS_METADATA_FILE
        with open(meta_path, "w") as f:
            json.dump(self.docs_metadata, f, indent=2)

    def clear_index(self):
        """Delete all vectors from Pinecone and reset metadata. Called on new session."""
        try:
            pinecone_index = self.pc.Index(self.index_name)
            pinecone_index.delete(delete_all=True)
            logger.info(f"Cleared all vectors from Pinecone index '{self.index_name}'")
        except Exception as e:
            logger.warning(f"Failed to clear Pinecone index: {e}")

        # Reset metadata
        self.docs_metadata = {}
        self._save_docs_metadata()

        # Rebuild clean index + query engine
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)
        self._create_query_engine()
        logger.info("Index cleared and ready for new documents")

    def load_documents(self, force_reload: bool = False):
        """Load and index documents from the data directory."""
        logger.info(f"Loading documents from {self.data_dir}")

        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return

        if force_reload:
            # Delete and recreate the Pinecone index
            logger.info("Force reload: deleting and recreating Pinecone index...")
            try:
                self.pc.delete_index(self.index_name)
            except Exception:
                pass
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            pinecone_index = self.pc.Index(self.index_name)
            self.vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
            self.docs_metadata = {}

        # Load documents
        reader = SimpleDirectoryReader(
            input_dir=str(self.data_dir),
            required_exts=[".pdf", ".md", ".txt", ".docx"],
            recursive=True,
        )
        documents = reader.load_data()
        logger.info(f"Loaded {len(documents)} document chunks")

        # Create index
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context
        )
        self._create_query_engine()

        # Track metadata
        for doc in documents:
            source = doc.metadata.get("file_name", "unknown")
            if source not in [m.get("filename") for m in self.docs_metadata.values()]:
                doc_id = str(uuid.uuid4())[:8]
                self.docs_metadata[doc_id] = {
                    "filename": source,
                    "filepath": str(doc.metadata.get("file_path", "")),
                    "status": "indexed",
                }
        self._save_docs_metadata()
        logger.info("Documents indexed in Pinecone")

    def add_document(self, file_path: str, original_filename: str) -> str:
        """Add a single document to the knowledge base."""
        logger.info(f"Adding document: {original_filename}")

        reader = SimpleDirectoryReader(input_files=[file_path])
        documents = reader.load_data()
        doc_id = str(uuid.uuid4())[:8]

        for doc in documents:
            doc.metadata["doc_id"] = doc_id
            doc.metadata["original_filename"] = original_filename

        if self.index:
            for doc in documents:
                self.index.insert(doc)
        else:
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            self.index = VectorStoreIndex.from_documents(
                documents, storage_context=storage_context
            )

        self._create_query_engine()

        self.docs_metadata[doc_id] = {
            "filename": original_filename,
            "filepath": file_path,
            "chunk_count": len(documents),
            "status": "indexed",
        }
        self._save_docs_metadata()

        logger.info(f"Document added: {original_filename} (ID: {doc_id}, {len(documents)} chunks)")
        return doc_id

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the knowledge base."""
        if doc_id not in self.docs_metadata:
            return False

        logger.info(f"Deleting document: {doc_id}")

        try:
            pinecone_index = self.pc.Index(self.index_name)
            pinecone_index.delete(filter={"doc_id": {"$eq": doc_id}})
        except Exception as e:
            logger.warning(f"Could not delete vectors from Pinecone: {e}")

        del self.docs_metadata[doc_id]
        self._save_docs_metadata()

        self.index = VectorStoreIndex.from_vector_store(self.vector_store)
        self._create_query_engine()

        logger.info(f"Document {doc_id} deleted")
        return True

    def list_documents(self) -> list[dict]:
        """List all indexed documents."""
        return [
            {"id": doc_id, **meta}
            for doc_id, meta in self.docs_metadata.items()
        ]

    def query(self, question: str) -> str:
        """Query the knowledge base."""
        if not self.query_engine:
            return "Knowledge base is empty. Please upload documents first."
        response = self.query_engine.query(question)
        return str(response)

    def query_with_sources(self, question: str) -> dict:
        """Query and return answer with source chunks."""
        if not self.query_engine:
            return {"answer": "Knowledge base is empty.", "sources": []}

        response = self.query_engine.query(question)
        answer = str(response)

        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                sources.append({
                    "text": node.text[:300] + "..." if len(node.text) > 300 else node.text,
                    "score": round(node.score, 3) if node.score else None,
                    "filename": node.metadata.get("file_name", node.metadata.get("original_filename", "unknown")),
                    "doc_id": node.metadata.get("doc_id", ""),
                })

        return {"answer": answer, "sources": sources}

    async def aquery(self, question: str) -> str:
        """Async query."""
        if not self.query_engine:
            return "Knowledge base is empty. Please upload documents first."
        response = await self.query_engine.aquery(question)
        return str(response)

    async def aquery_with_sources(self, question: str) -> dict:
        """Async query with sources."""
        if not self.query_engine:
            return {"answer": "Knowledge base is empty.", "sources": []}

        response = await self.query_engine.aquery(question)
        answer = str(response)

        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                sources.append({
                    "text": node.text[:300] + "..." if len(node.text) > 300 else node.text,
                    "score": round(node.score, 3) if node.score else None,
                    "filename": node.metadata.get("file_name", node.metadata.get("original_filename", "unknown")),
                    "doc_id": node.metadata.get("doc_id", ""),
                })

        return {"answer": answer, "sources": sources}
