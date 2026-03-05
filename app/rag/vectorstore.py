from langchain_community.vectorstores import FAISS
from app.core.config import settings
from app.utils.genai_adapter import GeminiEmbeddings
import os

def get_vectorstore():
    if os.path.exists(settings.CHROMA_PERSIST_DIR):
        local_embeddings = GeminiEmbeddings(model="models/gemini-embedding-001")
        vectordb = FAISS.load_local(
            settings.CHROMA_PERSIST_DIR, local_embeddings, allow_dangerous_deserialization=True
        )
        return vectordb
    else:
        raise ValueError(
            f"Vectorstore not found at {settings.CHROMA_PERSIST_DIR}. "
            "Run: python -m scripts.ingest_pdf"
        )

def get_retriever(k: int = 10):
    vectordb = get_vectorstore()
    return vectordb.as_retriever(search_kwargs={"k": k})

