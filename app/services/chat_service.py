# app/services/chat_service.py
"""
Service layer that:
- Receives a question string
- Calls the LangGraph RAG workflow
- Returns answer string
"""

import logging
import time
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any

from app.rag.graph import rag_graph
from app.utils.web_scraper import search_website, search_web_general
from app.rag.vectorstore import get_retriever
from app.utils.intent_engine import is_external_query
from app.core.config import settings
from app.utils.genai_adapter import GeminiChatModel

logger = logging.getLogger(__name__)

# Website URL to search
WEBSITE_URL = "https://ritzmediaworld.com"


@lru_cache(maxsize=1)
def _get_retriever_cached():
    return get_retriever(k=3)


def build_parallel_context(
    question: str,
    website_url: str = WEBSITE_URL,
    include_web: bool = True,
    developer_context: str = "",
) -> dict[str, Any]:
    docs = []
    web_content = ""

    def fetch_docs():
        try:
            retriever = _get_retriever_cached()
            return list(retriever.invoke(question) or [])
        except Exception as exc:
            logger.warning(f"⚠️ Doc retrieval error: {exc}")
            return []

    def fetch_web():
        if not include_web:
            return ""
        try:
            return search_website(question, website_url)
        except Exception as exc:
            logger.warning(f"⚠️ Web search error: {exc}")
            return ""

    with ThreadPoolExecutor(max_workers=2) as executor:
        docs_future = executor.submit(fetch_docs)
        web_future = executor.submit(fetch_web)
        docs = docs_future.result()
        web_content = web_future.result()

    return {
        "docs": docs,
        "web_context": web_content,
        "developer_context": (developer_context or "").strip(),
        "external_context": "",
    }


_LOW_CONFIDENCE_MARKERS = (
    "provided website information",
    "provided information from",
    "do not list",
    "does not list",
    "not listed",
    "not available in the context",
    "not available in context",
    "i couldn't find",
    "i could not find",
    "not found in the context",
    "cannot provide a specific list",
    "please contact us",
    "something went wrong",
    "i'm having trouble right now",
    "i could not find enough reliable information",
)


def needs_external_web_fallback(answer: str) -> bool:
    text = (answer or "").strip().lower()
    if not text:
        return True
    return any(marker in text for marker in _LOW_CONFIDENCE_MARKERS)


def _is_top_fm_query(question: str) -> bool:
    q = (question or "").lower()
    if "fm" not in q and "radio" not in q:
        return False
    return any(
        key in q
        for key in (
            "top fm",
            "best fm",
            "fm channels",
            "fm channel",
            "radio stations",
            "top radio",
            "best radio",
        )
    )


def _top_fm_channels_india_answer() -> str:
    # Keep this response concise and list-only per product requirement.
    return (
        "1. Radio Mirchi 98.3\n"
        "2. Red FM 93.5\n"
        "3. BIG FM 92.7\n"
        "4. Radio City 91.1 FM\n"
        "5. Fever FM 104\n"
        "6. AIR FM Rainbow\n"
        "7. AIR FM Gold\n"
        "8. Radio One 94.3 FM\n"
        "9. MY FM 94.3\n"
        "10. Ishq FM 104.8"
    )


def _is_top_newspaper_query(question: str) -> bool:
    q = (question or "").lower()
    if "newspaper" not in q and "news paper" not in q:
        return False
    return any(
        key in q
        for key in (
            "top newspaper",
            "best newspaper",
            "top newspapers",
            "best newspapers",
            "newspaper in india",
            "newspaper in delhi",
            "newspapers in india",
            "newspapers in delhi",
        )
    )


def _top_newspapers_answer(question: str) -> str:
    q = (question or "").lower()
    if "delhi" in q:
        return (
            "1. Hindustan Times\n"
            "2. The Times of India\n"
            "3. The Hindu (Delhi edition)\n"
            "4. The Indian Express\n"
            "5. The Statesman\n"
            "6. The Economic Times\n"
            "7. Navbharat Times\n"
            "8. Dainik Jagran\n"
            "9. Amar Ujala\n"
            "10. Jansatta"
        )
    return (
        "1. The Times of India\n"
        "2. Hindustan Times\n"
        "3. The Hindu\n"
        "4. The Indian Express\n"
        "5. Dainik Bhaskar\n"
        "6. Dainik Jagran\n"
        "7. Amar Ujala\n"
        "8. The Economic Times\n"
        "9. Anandabazar Patrika\n"
        "10. Malayala Manorama"
    )


def _is_agency_landscape_query(question: str) -> bool:
    q = (question or "").lower()
    has_agency_topic = any(token in q for token in ("agency", "agencies", "media company", "advertising company"))
    has_ranking_intent = any(token in q for token in ("top", "best", "list", "ranking", "compare", "vs"))
    has_geo = any(token in q for token in ("in india", "in delhi", "in ncr", "in mumbai", "in bangalore"))
    return has_agency_topic and (has_ranking_intent or has_geo)


def _is_social_performance_combo_query(question: str) -> bool:
    q = (question or "").lower()
    has_social = "social media" in q or "smm" in q
    has_perf = any(
        token in q
        for token in (
            "performance",
            "proformance",
            "performence",
            "perfomance",
            "ppc",
            "paid ad",
            "paid ads",
            "ads",
            "adds",
        )
    )
    return has_social and has_perf


def _is_video_production_query(question: str) -> bool:
    q = (question or "").lower()
    return any(token in q for token in ("video production", "video shoot", "video content", "ad film", "reel production"))


def _is_lead_generation_query(question: str) -> bool:
    q = (question or "").lower()
    return "lead generation" in q or "lead generations" in q or "generate leads" in q


def _is_next_step_query(question: str) -> bool:
    q = (question or "").lower()
    has_agency_intent = any(token in q for token in ("agency", "hire", "work with", "get started"))
    has_next_step = any(token in q for token in ("next step", "what next", "how to proceed", "how do we start", "start"))
    return has_agency_intent and has_next_step


def _social_performance_combo_answer() -> str:
    return (
        "Yes. We can run Social Media Management and Performance Ads together as one integrated plan.\n\n"
        "Typical execution includes:\n"
        "1. Audience and funnel strategy\n"
        "2. Creative + ad copy for each funnel stage\n"
        "3. Paid campaigns (Meta/Google) with weekly optimization\n"
        "4. Lead tracking, CPL/ROAS reporting, and scaling winners\n\n"
        "If you share your industry and monthly budget range, I can suggest a practical starting plan."
    )


def _video_production_answer() -> str:
    return (
        "Yes. We support video production within our Creative Services workflow.\n\n"
        "This usually covers:\n"
        "1. Concept and script\n"
        "2. Shoot planning and production\n"
        "3. Editing, motion graphics, and ad-ready cuts\n"
        "4. Platform-specific versions for Instagram, YouTube, and paid ads\n\n"
        "Share your objective (brand film, reels, product video, ad creatives), and we can recommend the right format."
    )


def _lead_generation_answer() -> str:
    return (
        "We help with lead generation through a combined SEO + paid media + landing page funnel.\n\n"
        "Typical approach:\n"
        "1. Define ICP and offer\n"
        "2. Build/optimize landing page and tracking\n"
        "3. Run Google/Meta campaigns and retargeting\n"
        "4. Optimize weekly for lead quality and CPL\n\n"
        "If you want, share your target location and budget and we can suggest the first campaign structure."
    )


def _next_step_answer() -> str:
    return (
        "Great next step is a short discovery call.\n\n"
        "Please share:\n"
        "1. Your business category\n"
        "2. Primary goal (leads, sales, awareness)\n"
        "3. Monthly budget range\n"
        "4. Target geography\n\n"
        "After that, we can suggest a practical plan and timeline."
    )


def _is_brand_work_query(question: str) -> bool:
    q = (question or "").lower()
    return (
        ("brand" in q or "client" in q or "portfolio" in q)
        and any(token in q for token in ("worked", "work", "top", "which", "who"))
    )


def _brand_work_answer_from_context(web_context: str) -> str:
    return (
        "Ritz Media World's website highlights portfolio work and 'Brands That Trust Us', "
        "but a public named top-brand list is not shown in the available content. "
        "You can review the work page here: https://ritzmediaworld.com/work.html"
    )


def _format_external_web_answer(external_context: str) -> str:
    lines = [line.rstrip() for line in external_context.splitlines() if line.strip()]
    selected = lines[:18]
    return "\n".join(selected)


def _extract_external_titles(external_context: str, max_titles: int = 5) -> list[str]:
    titles: list[str] = []
    for raw_line in external_context.splitlines():
        line = raw_line.strip()
        if not line.startswith("- "):
            continue
        title = line[2:].strip()
        title = re.sub(r"\s+-\s+\d{4}.*$", "", title)
        title = re.sub(r"\s+\|\s+.*$", "", title)
        if not title:
            continue
        if title.lower().startswith("source:"):
            continue
        if title not in titles:
            titles.append(title)
        if len(titles) >= max_titles:
            break
    return titles


@lru_cache(maxsize=1)
def _get_company_extractor_llm() -> GeminiChatModel:
    return GeminiChatModel(
        model="gemini-2.5-flash",
        temperature=0.1,
        max_output_tokens=220,
    )


def _extract_company_names_with_llm(question: str, external_context: str, max_names: int = 8) -> list[str]:
    if not settings.GEMINI_API_KEY or not external_context.strip():
        return []
    try:
        llm = _get_company_extractor_llm()
        prompt = f"""
Extract company/agency names from these web snippets for this user query:
{question}

Rules:
- Return only names explicitly present in snippets.
- Prefer Indian media/advertising/marketing agencies or media companies.
- One name per line. No numbering. No explanation.
- Maximum {max_names} names.

Snippets:
{external_context[:7000]}
"""
        resp = llm.invoke(prompt)
        content = getattr(resp, "content", str(resp))
        if isinstance(content, list):
            content = content[0].get("text", "") if content else ""
        lines = [line.strip(" -•\t") for line in str(content).splitlines() if line.strip()]
        names: list[str] = []
        for line in lines:
            line_low = line.lower()
            if line_low.startswith("source:") or line_low == "none":
                continue
            if line not in names:
                names.append(line)
            if len(names) >= max_names:
                break
        return names
    except Exception as exc:
        logger.warning("⚠️ Company-name extraction failed: %s", exc)
        return []


@lru_cache(maxsize=1)
def _get_general_fallback_llm() -> GeminiChatModel:
    return GeminiChatModel(
        model="gemini-2.5-flash",
        temperature=0.4,
        max_output_tokens=700,
    )


def _answer_with_general_gemini(
    question: str,
    developer_context: str = "",
    web_context: str = "",
) -> str:
    if not settings.GEMINI_API_KEY:
        return ""
    try:
        llm = _get_general_fallback_llm()
        prompt = f"""
You are a helpful marketing and business assistant for Ritz Media World.

When the website context is incomplete, still answer the user's query using your internal knowledge and practical best practices.
Do not reply with "I cannot find enough information" unless the question is impossible.
Keep the response concise, actionable, and professional.
-Return clean plain text only (no markdown).
-Do not use asterisks (*) or markdown bullets.
-Use short headings and numbered points when useful.
-Add subheadings only when needed for clarity.


DEVELOPER NOTES:
{(developer_context or "").strip()}

WEBSITE CONTEXT (optional):
{(web_context or "")[:3500]}

USER QUESTION:
{question}
"""
        resp = llm.invoke(prompt)
        text = (getattr(resp, "content", "") or "").strip()
        return text
    except Exception as exc:
        logger.warning("General Gemini fallback failed: %s", exc)
        return ""


def _fallback_india_agency_names(max_names: int = 8) -> list[str]:
    # Practical fallback list for India-focused media/advertising agency queries
    # when web snippets are unavailable/noisy.
    base = [
        "GroupM India",
        "Dentsu India",
        "Madison Media",
        "Havas Media India",
        "Publicis Media India",
        "IPG Mediabrands India",
        "Omnicom Media Group India",
        "Initiative India",
    ]
    return base[:max_names]


def _clean_internal_answer(text: str) -> str:
    cleaned = (text or "").strip()
    lower = cleaned.lower()
    if any(
        marker in lower
        for marker in (
            "something went wrong",
            "i'm having trouble right now",
            "please contact us",
            "info@ritzmediaworld.com",
            "+91-7290002168",
        )
    ):
        return ""
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"(and|or|the)\s*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r",\s*$", "", cleaned)
    cleaned = re.sub(r"([,;:])\.", ".", cleaned)
    return cleaned


def _compose_professional_blended_answer(
    question: str,
    internal_answer: str,
    external_context: str,
) -> str:
    clean_internal = _clean_internal_answer(internal_answer)
    titles = _extract_external_titles(external_context, max_titles=6)
    company_names = _extract_company_names_with_llm(question, external_context, max_names=8)

    if _is_agency_landscape_query(question):
        if (
            not clean_internal
            or "*" in (internal_answer or "")
            or "according to their website" in (internal_answer or "").lower()
        ):
            clean_internal = (
                "Ritz Media World is presented in its own materials as a leading advertising and "
                "digital media agency, particularly in Delhi NCR."
            )
        if not company_names and not titles:
            company_names = _fallback_india_agency_names(max_names=8)
        if not company_names:
            company_names = _fallback_india_agency_names(max_names=8)

        if company_names:
            names = ", ".join(company_names)
            clean_internal = clean_internal.rstrip(".")
            return (
                f"{clean_internal}. Looking beyond Ritz, commonly cited media/advertising players in India include: "
                f"{names}."
            )
        names = "; ".join(titles)
        clean_internal = clean_internal.rstrip(".")
        return (
            f"{clean_internal}. To broaden the view across India, external industry listings and reviews "
            f"frequently mention: {names}."
        )

    if not titles and not company_names:
        return clean_internal or "I could not find enough reliable information to answer this accurately."

    return (
        f"{clean_internal}. Additional external references: " + "; ".join(titles)
        if clean_internal
        else "Additional external references: " + "; ".join(titles)
    )


def extract_founded_year_answer(question: str, docs: list[Any], web_context: str) -> str:
    q = (question or "").lower()
    if "ritz" not in q:
        return ""
    if not any(token in q for token in ("founded", "established", "since", "which year", "when")):
        return ""

    candidates: list[str] = []
    candidates.extend(re.findall(r"\b(19\d{2}|20\d{2})\b", web_context or ""))
    for doc in docs or []:
        candidates.extend(re.findall(r"\b(19\d{2}|20\d{2})\b", getattr(doc, "page_content", "") or ""))

    # Prefer plausible founding years (avoid future years for this query type).
    plausible = [int(y) for y in candidates if 1900 <= int(y) <= 2026]
    if not plausible:
        return ""

    # Website content for Ritz repeatedly mentions 2008 as start year.
    if 2008 in plausible:
        return "Ritz Media World was founded in 2008."

    year = min(plausible)
    return f"Ritz Media World was founded in {year}."


def run_chat_with_web(
    question: str,
    include_web: bool = True,
    developer_context: str = "",
) -> dict:
    """
    Run the RAG graph for a single user question with web search.
    Returns dict with 'answer' and 'has_answer' flag.
    """
    start = time.time()
    logger.info(f"📥 Question: {question[:80]}")

    # Deterministic fast path for top FM channel queries.
    if _is_top_fm_query(question):
        elapsed = time.time() - start
        logger.info(f"⏱️ Total time: {elapsed:.2f}s (top-fm fast path)")
        return {"answer": _top_fm_channels_india_answer(), "has_answer": True}
    if _is_social_performance_combo_query(question):
        elapsed = time.time() - start
        logger.info(f"?? Total time: {elapsed:.2f}s (social+performance fast path)")
        return {"answer": _social_performance_combo_answer(), "has_answer": True}
    if _is_video_production_query(question):
        elapsed = time.time() - start
        logger.info(f"?? Total time: {elapsed:.2f}s (video-production fast path)")
        return {"answer": _video_production_answer(), "has_answer": True}
    if _is_lead_generation_query(question):
        elapsed = time.time() - start
        logger.info(f"?? Total time: {elapsed:.2f}s (lead-generation fast path)")
        return {"answer": _lead_generation_answer(), "has_answer": True}
    if _is_next_step_query(question):
        elapsed = time.time() - start
        logger.info(f"?? Total time: {elapsed:.2f}s (next-step fast path)")
        return {"answer": _next_step_answer(), "has_answer": True}
    if _is_top_newspaper_query(question):
        elapsed = time.time() - start
        logger.info(f"⏱️ Total time: {elapsed:.2f}s (top-newspaper fast path)")
        return {"answer": _top_newspapers_answer(question), "has_answer": True}

    state = {
        "question": question,
        "docs": [],
        "answer": "",
        "web_context": "",
        "developer_context": "",
        "external_context": "",
    }

    context_bundle = build_parallel_context(
        question=question,
        website_url=WEBSITE_URL,
        include_web=include_web,
        developer_context=developer_context,
    )
    state.update(context_bundle)
    logger.info(
        "⚡ Context ready in parallel | docs=%d web_chars=%d dev_chars=%d",
        len(state.get("docs", [])),
        len(state.get("web_context", "")),
        len(state.get("developer_context", "")),
    )

    try:
        if _is_brand_work_query(question):
            elapsed = time.time() - start
            logger.info(f"⏱️ Total time: {elapsed:.2f}s (brand-work fast path)")
            return {
                "answer": _brand_work_answer_from_context(state.get("web_context", "")),
                "has_answer": True,
            }

        # Deterministic fast path for year-foundation queries.
        founded_year_answer = extract_founded_year_answer(
            question=question,
            docs=state.get("docs", []),
            web_context=state.get("web_context", ""),
        )
        if founded_year_answer:
            elapsed = time.time() - start
            logger.info(f"⏱️ Total time: {elapsed:.2f}s (founded-year fast path)")
            return {"answer": founded_year_answer, "has_answer": True}

        result_state = rag_graph.invoke(state)
        answer = result_state.get("answer", "").strip()

        should_fetch_external = is_external_query(question) or (
            needs_external_web_fallback(answer) and _is_agency_landscape_query(question)
        )
        if should_fetch_external:
            is_media_query = _is_agency_landscape_query(question)
            if is_media_query:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    external_future = executor.submit(search_web_general, question, 5)
                    names_future = executor.submit(
                        search_web_general,
                        f"{question} company names list",
                        5,
                    )
                    external_context = external_future.result()
                    names_context = names_future.result()
                if names_context:
                    external_context = f"{external_context}\n\n{names_context}"
            else:
                external_context = search_web_general(question, max_results=3)
            logger.info("🌍 Running external web fallback for: %s", question[:60])
            logger.info("🌍 External web context size: %d chars", len(external_context))
            external_answer = _format_external_web_answer(external_context) if external_context else ""
            answer = _compose_professional_blended_answer(
                question=question,
                internal_answer=answer,
                external_context=external_answer,
            )

        # If answer is still low-confidence, ask Gemini to answer using general knowledge.
        if needs_external_web_fallback(answer):
            general_answer = _answer_with_general_gemini(
                question=question,
                developer_context=developer_context,
                web_context=state.get("web_context", ""),
            )
            if general_answer:
                answer = general_answer

        elapsed = time.time() - start
        logger.info(f"⏱️ Total time: {elapsed:.2f}s")

        if not answer:
            return {
                "answer": (
                    "I couldn't find a specific answer for that.\n"
                    "Feel free to ask about our services, or contact us:\n"
                    "📞 +91-7290002168\n"
                    "📧 info@ritzmediaworld.com"
                ),
                "has_answer": False
            }

        return {
            "answer": answer,
            "has_answer": True
        }

    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"❌ RAG error after {elapsed:.2f}s: {str(e)}")
        return {
            "answer": (
                "I'm having trouble right now. Please contact us:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            ),
            "has_answer": False
        }


def run_chat(question: str, developer_context: str = "") -> dict:
    """Run chat with web search enabled by default"""
    return run_chat_with_web(
        question,
        include_web=True,
        developer_context=developer_context,
    )
