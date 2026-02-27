from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings
import os

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.GEMINI_API_KEY
)

def get_vectorstore():
    if os.path.exists(settings.CHROMA_PERSIST_DIR):
        local_embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=settings.GEMINI_API_KEY
        )
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

