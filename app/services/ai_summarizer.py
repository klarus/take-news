"""
Sintesi AI degli eventi usando Gemini 1.5 Flash (default) o Groq.
Swappabile via env AI_PROVIDER=gemini|groq
"""
import os
import httpx
from ..models.news import Article

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _build_prompt(topic: str, articles: list[Article]) -> str:
    sources_text = "\n".join(
        f"- [{a.source}] {a.title}: {a.snippet or '(nessun estratto)'}"
        for a in articles
    )
    return f"""Sei un giornalista italiano che sintetizza notizie da più fonti.
REGOLE ASSOLUTE:
- Rispondi SEMPRE e SOLO in italiano, anche se gli articoli sono in inglese o altra lingua.
- NON usare markdown, grassetto, corsivo o asterischi.
- Inizia la risposta esattamente con "TITOLO:" senza spazi o caratteri prima.

Topic: {topic}
Articoli da {len(articles)} fonti diverse:
{sources_text}

Scrivi:
1. TITOLO: un titolo chiaro e neutro dell'evento in italiano (max 15 parole)
2. SINTESI: un paragrafo di 3-4 frasi in italiano che riassume l'evento, basandoti solo su ciò che è confermato da più fonti. Sii neutrale e fattuale.

Formato risposta (esattamente così, nient'altro):
TITOLO: <titolo in italiano>
SINTESI: <sintesi in italiano>"""


async def summarize_event(topic: str, articles: list[Article]) -> tuple[str, str]:
    """Restituisce (headline, summary)."""
    prompt = _build_prompt(topic, articles)

    if AI_PROVIDER == "groq":
        return await _call_groq(prompt, articles)
    return await _call_gemini(prompt, articles)


async def _call_gemini(prompt: str, articles: list[Article]) -> tuple[str, str]:
    if not GEMINI_API_KEY:
        return _fallback(articles)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json=payload,
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return _parse_response(text, articles)
    except Exception:
        return _fallback(articles)


async def _call_groq(prompt: str, articles: list[Article]) -> tuple[str, str]:
    if not GROQ_API_KEY:
        return _fallback(articles)
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GROQ_URL,
                json=payload,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            return _parse_response(text, articles)
    except Exception:
        return _fallback(articles)


import re as _re

def _clean(s: str) -> str:
    # rimuove markdown bold/italic (**/*/__)
    return _re.sub(r"[\*_]+", "", s).strip()

def _parse_response(text: str, articles: list[Article]) -> tuple[str, str]:
    headline = ""
    summary = ""
    # normalizza: rimuove markdown e cerca le label in modo flessibile
    for line in text.strip().splitlines():
        clean = _clean(line)
        low = clean.lower()
        if low.startswith("titolo:"):
            headline = clean[len("titolo:"):].strip()
        elif low.startswith("sintesi:"):
            summary = clean[len("sintesi:"):].strip()
    if not headline:
        headline = articles[0].title if articles else "Notizia"
    if not summary:
        summary = articles[0].snippet or ""
    return headline, summary


def _fallback(articles: list[Article]) -> tuple[str, str]:
    """Usato se nessuna API key è configurata (sviluppo)."""
    headline = articles[0].title if articles else "Notizia"
    snippets = [a.snippet for a in articles if a.snippet]
    summary = snippets[0] if snippets else "Sintesi non disponibile (configura GEMINI_API_KEY)."
    return headline, summary
