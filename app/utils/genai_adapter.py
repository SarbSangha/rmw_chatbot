import asyncio
import importlib.util
import logging
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, AsyncGenerator

from langchain_core.embeddings import Embeddings

from app.core.config import settings

logger = logging.getLogger(__name__)

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module=r"langchain_google_genai.*",
)
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module=r"langchain_google_genai.*",
)


@dataclass
class LLMResponse:
    content: str


def _message_to_text(message: Any) -> str:
    role = getattr(message, "type", "user")
    content = getattr(message, "content", "")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text_val = item.get("text")
                if isinstance(text_val, str):
                    parts.append(text_val)
                elif text_val is not None:
                    parts.append(str(text_val))
            elif item is not None:
                parts.append(str(item))
        content = "".join(parts)
    return f"{role.upper()}: {content}"


def _messages_to_prompt(messages_or_text: Any) -> str:
    if isinstance(messages_or_text, str):
        return messages_or_text
    if isinstance(messages_or_text, list):
        return "\n\n".join(_message_to_text(msg) for msg in messages_or_text)
    return str(messages_or_text)


def _extract_text_from_chunk(chunk: Any) -> str:
    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, dict):
        dict_text = chunk.get("text")
        if isinstance(dict_text, str):
            return dict_text
    text = getattr(chunk, "text", None)
    if isinstance(text, str):
        return text
    candidates = getattr(chunk, "candidates", None) or []
    parts: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        chunk_parts = getattr(content, "parts", None) if content is not None else None
        if not chunk_parts:
            continue
        for part in chunk_parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str):
                parts.append(part_text)
    return "".join(parts)


def _google_genai_available() -> bool:
    return importlib.util.find_spec("google.genai") is not None


@lru_cache(maxsize=1)
def get_genai_client() -> Any:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")
    if not _google_genai_available():
        raise ImportError("google.genai is not installed in this environment.")
    from google import genai

    return genai.Client(api_key=settings.GEMINI_API_KEY)


class GeminiChatModel:
    def __init__(
        self,
        model: str,
        temperature: float = 0.3,
        max_output_tokens: int = 1200,
        top_p: float = 0.95,
        top_k: int = 40,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.top_p = top_p
        self.top_k = top_k
        self._fallback_llm: Any = None

        if not _google_genai_available():
            warnings.filterwarnings(
                "ignore",
                category=FutureWarning,
                module=r"langchain_google_genai.*",
            )
            warnings.filterwarnings(
                "ignore",
                category=UserWarning,
                module=r"langchain_google_genai.*",
            )
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._fallback_llm = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
                top_p=self.top_p,
                top_k=self.top_k,
                max_retries=0,
                request_timeout=20,
            )

    def _config(self) -> Any:
        from google.genai import types

        return types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            top_p=self.top_p,
            top_k=self.top_k,
        )

    def invoke(self, messages_or_text: Any) -> LLMResponse:
        if self._fallback_llm is not None:
            response = self._fallback_llm.invoke(messages_or_text)
            return LLMResponse(content=_extract_text_from_chunk(getattr(response, "content", response)).strip())

        prompt = _messages_to_prompt(messages_or_text)
        client = get_genai_client()
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._config(),
        )
        return LLMResponse(content=_extract_text_from_chunk(response).strip())

    async def astream(self, messages_or_text: Any) -> AsyncGenerator[LLMResponse, None]:
        if self._fallback_llm is not None:
            async for chunk in self._fallback_llm.astream(messages_or_text):
                chunk_text = _extract_text_from_chunk(getattr(chunk, "content", chunk))
                if chunk_text:
                    yield LLMResponse(content=chunk_text)
            return

        prompt = _messages_to_prompt(messages_or_text)

        def _stream_text_chunks() -> list[str]:
            client = get_genai_client()
            text_chunks: list[str] = []
            for chunk in client.models.generate_content_stream(
                model=self.model,
                contents=prompt,
                config=self._config(),
            ):
                text = _extract_text_from_chunk(chunk)
                if text:
                    text_chunks.append(text)
            return text_chunks

        chunks = await asyncio.to_thread(_stream_text_chunks)
        for chunk_text in chunks:
            yield LLMResponse(content=chunk_text)


class GeminiEmbeddings(Embeddings):
    def __init__(self, model: str = "gemini-embedding-001") -> None:
        self.model = model
        self._fallback_embeddings: Any = None
        if not _google_genai_available():
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            self._fallback_embeddings = GoogleGenerativeAIEmbeddings(
                model=self.model,
                google_api_key=settings.GEMINI_API_KEY,
            )

    @staticmethod
    def _extract_vector(item: Any) -> list[float]:
        values = getattr(item, "values", None)
        if isinstance(values, list):
            return [float(x) for x in values]
        if isinstance(item, dict):
            dict_values = item.get("values")
            if isinstance(dict_values, list):
                return [float(x) for x in dict_values]
        return []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._fallback_embeddings is not None:
            return self._fallback_embeddings.embed_documents(texts)

        if not texts:
            return []
        client = get_genai_client()
        from google.genai import types

        response = client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        embeddings = getattr(response, "embeddings", None) or []
        return [self._extract_vector(item) for item in embeddings]

    def embed_query(self, text: str) -> list[float]:
        if self._fallback_embeddings is not None:
            return self._fallback_embeddings.embed_query(text)

        client = get_genai_client()
        from google.genai import types

        response = client.models.embed_content(
            model=self.model,
            contents=[text],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        embeddings = getattr(response, "embeddings", None) or []
        if not embeddings:
            return []
        return self._extract_vector(embeddings[0])
