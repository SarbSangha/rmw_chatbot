# app/rag/ingest.py
"""
This script is run manually (or via scripts/ingest_pdf.py) to:
- Load the PDF
- Split it into chunks
- Embed and store in Chroma vector DB
"""

# app/rag/ingest.py
from langchain_community.document_loaders import Docx2txtLoader  # <-- CHANGED
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logging import logger

def build_vectorstore():
    logger.info("Loading document from %s", settings.PDF_PATH)
    loader = Docx2txtLoader(settings.PDF_PATH)  # <-- CHANGED
    docs = loader.load()
    # ... rest unchanged


    # 2. Split into smaller text chunks (better for retrieval)
    logger.info("Splitting document into chunks")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    chunks = splitter.split_documents(docs)

    # 3. Create embeddings for each chunk
    logger.info("Creating embeddings")
    embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)

    # 4. Store in Chroma and persist to disk
    logger.info("Building Chroma vector store in %s", settings.CHROMA_PERSIST_DIR)
    vectordb = Chroma.from_documents(
        chunks,
        embedding=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )
    vectordb.persist()
    logger.info("Vector store built and persisted successfully")


if __name__ == "__main__":
    build_vectorstore()
