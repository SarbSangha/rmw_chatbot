# app/rag/ingest.py
"""
This script is run manually (or via scripts/ingest_pdf.py) to:
- Load the source DOCX
- Split it into chunks
- Embed and store in a FAISS vector DB
"""

from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.core.logging import logger

def build_vectorstore():
    logger.info("Loading document from %s", settings.PDF_PATH)
    loader = Docx2txtLoader(settings.PDF_PATH)
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
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=settings.GEMINI_API_KEY
    )

    # 4. Store in FAISS and persist to disk
    logger.info("Building FAISS vector store in %s", settings.CHROMA_PERSIST_DIR)
    vectordb = FAISS.from_documents(
        chunks,
        embedding=embeddings,
    )
    vectordb.save_local(settings.CHROMA_PERSIST_DIR)  # save_local instead of persist

if __name__ == "__main__":
    build_vectorstore()
