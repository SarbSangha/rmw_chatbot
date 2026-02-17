# scripts/ingest_pdf.py
"""
Helper script to trigger RAG ingest from CLI.

Usage:
    python -m scripts.ingest_pdf
"""

from app.rag.ingest import build_vectorstore


def main():
    build_vectorstore()


if __name__ == "__main__":
    main()
