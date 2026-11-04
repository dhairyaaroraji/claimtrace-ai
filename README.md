# ClaimTrace AI

### Live Claim Verification & Freshness Intelligence

**Every AI claim. Traced. Verified. Fresh.**

ClaimTrace AI is a hackathon MVP for finding claims in AI-generated answers, checking each claim against live web results, and surfacing evidence, source dates, and freshness signals.

## What it does

1. Accepts a pasted AI-generated answer.
2. Splits it into factual claims. When configured, a Bifrost-compatible model extracts concise claims; a deterministic local extractor is the fallback.
3. Searches the live web with Tavily for each claim (or uses clearly marked sample evidence when Tavily is not configured).
4. Labels claims as Supported, Needs review, or No evidence, with links, available publication dates, and an age-based freshness indicator.
5. Computes a transparent overall score from evidence support and source freshness.

The app never treats a search result as proof. Its status is a triage signal for human review, and the evidence panel shows what the web search returned.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # optional; add API keys to enable live integrations
python app.py
```

Open http://localhost:8000. Without keys, the UI runs in demo mode with sample results. To use live web search, set `TAVILY_API_KEY`. To enable model-assisted claim extraction through Bifrost, also set `BIFROST_BASE_URL`, `BIFROST_API_KEY`, and `BIFROST_MODEL`.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `TAVILY_API_KEY` | Live web search and evidence | unset (sample mode) |
| `BIFROST_BASE_URL` | OpenAI-compatible Bifrost gateway base URL | unset (local extractor) |
| `BIFROST_API_KEY` | Bifrost virtual key | unset |
| `BIFROST_MODEL` | Model configured in the gateway | `openai/gpt-4o-mini` |
| `PORT` | HTTP port | `8000` |
| `MAX_ANSWER_CHARS` | Input size limit | `12000` |
| `MAX_CLAIMS` | Maximum claims searched per request | `8` |

The Bifrost adapter sends an OpenAI-compatible `POST {BIFROST_BASE_URL}/chat/completions` request. Configure upstream providers, model names, and routing rules in your own Bifrost installation. The app does not claim Bifrost is connected unless the environment is configured and the request succeeds.

## AI and evidence design

- **Bifrost** is the optional model gateway and routing layer for claim extraction. One OpenAI-compatible endpoint lets the deployment choose or route the extraction model without coupling the app to one provider.
- **Tavily** provides current search snippets and source URLs for claim-level web research.
- **Local fallback** extracts sentence-like statements with regular expressions and scores Tavily-style sample evidence deterministically. It does not call an AI model or the live web.
- **Freshness** uses source publication dates when available. If a source has no date, the interface says “Date unavailable” rather than inventing one. The overall score is the average of claim scores; per-claim scoring weights evidence match (65%) and recency (35%).
- Search snippets are untrusted data and are escaped before display. API credentials remain server-side and are never returned to the browser.

## API

`POST /api/analyze`

```json
{ "answer": "Paste an AI-generated answer here." }
```

Returns an analysis timestamp, overall score, integration mode, and each claim's status, freshness score, evidence text, URL, and publication date when available.

`GET /api/health` reports configured integrations without exposing secrets.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests cover claim extraction, date/freshness scoring, status classification, API input validation, and safe no-key demo mode.

## Deploy

### Render

1. Push this folder to a public GitHub repository.
2. Create a Render **Web Service** from that repository.
3. Runtime: Python; Build command: `pip install -r requirements.txt`; Start command: `python app.py`.
4. Add `TAVILY_API_KEY` and the optional Bifrost variables in Render's environment settings.
5. Deploy and open the generated HTTPS URL. Never commit `.env` or provider keys.

### Docker

```bash
docker build -t claimtrace-ai .
docker run --rm -p 8000:8000 --env-file .env claimtrace-ai
```

## Scope and limitations

Search relevance is not entailment. This MVP surfaces supporting or conflicting snippets for human inspection; it can miss sources, misread context, and cannot guarantee factual correctness. Source dates are only shown when provided by the search provider. For production, add provider quotas, request-level rate limiting, richer entailment evaluation, audit logging, and privacy controls appropriate to your deployment.

## Hackathon submission details

- **Project title:** ClaimTrace AI
- **Subtitle:** Live Claim Verification & Freshness Intelligence
- **Problem statement:** Build a Stale-Answer Detector for AI Applications
- **Demo video:** None (intentionally not created)
- **Pitch deck:** Create separately (intentionally not included)

