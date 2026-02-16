"""Initialize RAG index by loading and indexing documents into Pinecone."""

import logging
from dotenv import load_dotenv
from rag import RAGEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Initialize the RAG engine with documents from Data/ folder."""
    load_dotenv(".env")

    logger.info("Initializing RAG engine (Pinecone + Google Embeddings + Cerebras LLM)...")

    rag_engine = RAGEngine(
        data_dir="Data",
        prompt_file="Prompt/prompt.md",
        index_name="knowledge-base",
        embedding_model="gemini-embedding-001",
        llm_model="llama-3.3-70b",
    )

    # Load and index documents
    logger.info("Loading and indexing documents...")
    rag_engine.load_documents(force_reload=True)

    # Test query
    logger.info("Testing RAG engine with sample query...")
    result = rag_engine.query_with_sources("What information is available?")
    logger.info(f"\nTest Answer: {result['answer']}")
    logger.info(f"Sources: {len(result['sources'])} chunks retrieved\n")

    logger.info("RAG initialization complete!")


if __name__ == "__main__":
    main()
