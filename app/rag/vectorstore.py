# app/rag/vectorstore.py
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

# We create a single embeddings object and Chroma instance.
# This assumes that the DB has already been created by ingest.py.
_embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)


def get_vectorstore() -> Chroma:
    """
    Load the existing Chroma vector store from disk.
    It expects that 'ingest.py' already created and persisted it.
    """
    vectordb = Chroma(
        embedding_function=_embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )
    return vectordb


def get_retriever(k: int = 10):
    vectordb = get_vectorstore()
    return vectordb.as_retriever(search_kwargs={"k": k})

