"""ClaimTrace AI: small stdlib web app with optional Tavily and Bifrost adapters."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent


def load_dotenv() -> None:
    """Load simple KEY=VALUE entries without overriding the process environment."""
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()


def env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def extract_claims(answer: str, limit: int = 8) -> list[str]:
    """Conservative sentence splitter used when no Bifrost model is configured."""
    chunks = re.split(r"(?<=[.!?])\s+|\n+|(?<=;)\s+", answer.strip())
    claims = []
    for chunk in chunks:
        text = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", chunk).strip()
        text = re.sub(r"\s+", " ", text)
        if len(text) >= 24 and re.search(r"\b(is|are|was|were|has|have|had|will|can|costs?|launched|increased|decreased|located|founded|reached|contains|requires|provides|offers|became|stands)\b|\d", text, re.I):
            if text not in claims:
                claims.append(text)
        if len(claims) >= limit:
            break
    return claims


def model_claims(answer: str, limit: int) -> list[str] | None:
    base, key = os.getenv("BIFROST_BASE_URL", "").rstrip("/"), os.getenv("BIFROST_API_KEY", "")
    if not base or not key:
        return None
    body = {"model": os.getenv("BIFROST_MODEL", "openai/gpt-4o-mini"), "temperature": 0, "messages": [
        {"role": "system", "content": f"Extract up to {limit} independently verifiable factual claims from the answer. Return only a JSON array of strings. Do not add facts."},
        {"role": "user", "content": answer},
    ]}
    try:
        req = Request(base + "/chat/completions", data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=25) as response:
            content = json.loads(response.read()).get("choices", [{}])[0].get("message", {}).get("content", "")
        match = re.search(r"\[.*\]", content, re.S)
        values = json.loads(match.group(0)) if match else []
        if isinstance(values, list):
            claims = [re.sub(r"\s+", " ", str(x)).strip() for x in values if str(x).strip()]
            if claims:
                return claims[:limit]
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError):
        return None
    return None


def search_tavily(claim: str) -> list[dict] | None:
    key = os.getenv("TAVILY_API_KEY", "")
    if not key:
        return None
    payload = {"api_key": key, "query": claim, "topic": "general", "search_depth": "basic", "max_results": 4, "include_answer": False}
    req = Request("https://api.tavily.com/search", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=20) as response:
        results = json.loads(response.read()).get("results", [])
    return [{"title": str(x.get("title", "Untitled source"))[:240], "url": x.get("url", ""), "content": str(x.get("content", ""))[:1200], "published_date": x.get("published_date")} for x in results[:4] if x.get("url", "").startswith(("https://", "http://"))]


def demo_sources(claim: str) -> list[dict]:
    return [{"title": "Demo evidence · live search not configured", "url": "https://docs.tavily.com/", "content": f"Sample evidence only. Configure TAVILY_API_KEY to search live sources for: {claim}", "published_date": None}]


def freshness(source: dict, now: datetime | None = None) -> tuple[int, str, int | None]:
    date_text = source.get("published_date")
    if not date_text:
        return 45, "Date unavailable", None
    try:
        published = datetime.fromisoformat(str(date_text).replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        reference = now or datetime.now(timezone.utc)
        days = max(0, (reference - published).days)
        score = max(0, min(100, round(100 * (0.5 ** (days / 365)))))
        label = "Today" if days == 0 else "1 day ago" if days == 1 else f"{days} days ago"
        return score, label, days
    except (TypeError, ValueError):
        return 45, "Date unavailable", None


def analyze_claim(claim: str, sources: list[dict], demo: bool) -> dict:
    if demo:
        status, support, rationale = "demo", 0, "Sample result. Add a Tavily key to check this claim against current sources."
    elif not sources:
        status, support, rationale = "unsupported", 0, "No web results were returned for this claim."
    else:
        # Search relevance is a triage signal. Keep the wording explicit; do not claim entailment.
        best = max(sources, key=lambda s: len(s.get("content", "")))
        lexical = set(re.findall(r"[a-z0-9]{4,}", claim.lower()))
        evidence = set(re.findall(r"[a-z0-9]{4,}", " ".join(s.get("content", "") for s in sources).lower()))
        overlap = len(lexical & evidence) / max(len(lexical), 1)
        status = "supported" if overlap >= .25 else "review"
        support = 90 if status == "supported" else 58
        rationale = "Relevant terms appear in the returned search snippets; inspect the linked sources to confirm context." if status == "supported" else "Search results were found, but snippet overlap is weak. Review the sources manually."
    source_scores = [freshness(s) for s in sources]
    recent = max((row[0] for row in source_scores), default=45)
    score = round(support * .65 + recent * .35) if not demo else 50
    label = "Fresh" if recent >= 75 else "Check age" if recent >= 40 else "Potentially stale"
    return {"text": claim, "status": status, "freshness_score": score, "freshness_label": label,
            "rationale": rationale, "sources": [{**s, "age_label": freshness(s)[1]} for s in sources]}


def analyze(answer: str) -> dict:
    max_claims = env_int("MAX_CLAIMS", 8)
    claims = model_claims(answer, max_claims)
    mode = "bifrost" if claims else "local"
    claims = claims or extract_claims(answer, max_claims)
    if not claims:
        raise ValueError("No verifiable claims found. Try a longer answer with factual statements.")
    results = []
    tavily_enabled = bool(os.getenv("TAVILY_API_KEY"))
    for claim in claims:
        sources = search_tavily(claim) if tavily_enabled else None
        results.append(analyze_claim(claim, sources if sources is not None else demo_sources(claim), demo=sources is None))
    active = [x["freshness_score"] for x in results if x["status"] != "demo"]
    score = round(sum(active) / len(active)) if active else None
    return {"analyzed_at": datetime.now(timezone.utc).isoformat(), "overall_score": score, "claim_count": len(results),
            "mode": mode, "search_mode": "tavily" if tavily_enabled else "demo", "claims": results}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self' data:")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            body = json.dumps({"ok": True, "tavily_configured": bool(os.getenv("TAVILY_API_KEY")), "bifrost_configured": bool(os.getenv("BIFROST_BASE_URL") and os.getenv("BIFROST_API_KEY"))}).encode()
            self._send(200, body, "application/json; charset=utf-8")
        else:
            path = "/index.html" if self.path == "/" else self.path
            target = (ROOT / "static" / path.lstrip("/")).resolve()
            if not target.is_relative_to((ROOT / "static").resolve()) or not target.is_file():
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            content_type = "text/html; charset=utf-8" if target.suffix == ".html" else "text/css; charset=utf-8" if target.suffix == ".css" else "text/javascript; charset=utf-8"
            self._send(200, target.read_bytes(), content_type)

    def do_POST(self) -> None:
        if self.path != "/api/analyze":
            self._send(404, b'{"error":"Not found"}', "application/json; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 25000:
                raise ValueError("Request is too large.")
            payload = json.loads(self.rfile.read(length))
            answer = payload.get("answer", "") if isinstance(payload, dict) else ""
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Paste an AI-generated answer first.")
            if len(answer) > env_int("MAX_ANSWER_CHARS", 12000):
                raise ValueError("Answer is too long. Please shorten it and try again.")
            result = analyze(answer)
            self._send(200, json.dumps(result).encode(), "application/json; charset=utf-8")
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, json.dumps({"error": str(exc)}).encode(), "application/json; charset=utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            self._send(502, json.dumps({"error": "A configured provider could not complete the request. Check its key, URL, quota, and connectivity.", "provider_error": str(exc)[:240]}).encode(), "application/json; charset=utf-8")

    def log_message(self, fmt: str, *args: object) -> None:
        # Avoid logging user answer text; BaseHTTPRequestHandler logs only method/path/status.
        super().log_message(fmt, *args)


if __name__ == "__main__":
    port = env_int("PORT", 8000)
    print(f"ClaimTrace AI listening on http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()

