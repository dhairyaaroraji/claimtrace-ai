# ClaimTrace AI

### Live Claim Verification & Freshness Intelligence

**Every AI claim. Traced. Verified. Fresh.**

ClaimTrace AI is a solo entry for the Geek Room AI Global Hackathon 2026, under **Build a Stale-Answer Detector for AI Applications**. It explores a common failure in AI applications: an answer can sound confident even after a price, API, rule, or policy has changed.

The Round 1 presentation describes the intended product and roadmap. This repository contains a working MVP. The MVP and the presentation are at different stages, so this README distinguishes implemented behavior from planned design.

## What works in this MVP

- Paste an AI-generated answer into the web interface.
- Extract factual-looking sentences with a local sentence-based extractor, or use optional Bifrost-assisted claim extraction.
- Search Tavily for each claim when `TAVILY_API_KEY` is configured.
- Show claim-level search snippets, source links, dates when available, and age labels.
- Assign simple triage labels: likely relevant, needs review, no evidence, or demo only.
- Display per-claim freshness signals and an overall score when live search is active.
- Run without credentials in a clearly labeled demo mode. Demo evidence is sample content and is not a live verification result.

## What the MVP does not claim

The current verdict is based on lexical overlap between a claim and Tavily's returned snippets. It does not use an LLM to determine whether the evidence entails or contradicts the claim. It does not yet compare independent sources, assess source reliability, or weight time-sensitive claim categories differently. A relevant snippet may still be incomplete or misleading, so users should open the linked sources and review important claims themselves.

The deck's proposed LLM verification, three-signal scoring (recency, source agreement, and reliability), and evaluation on a labeled answer set are roadmap items. No accuracy, stale-detection, latency, or cost benchmark results are reported yet.

## How the current MVP works

1. The browser sends the answer to the Python application server.
2. Claim extraction uses Bifrost when configured and available; otherwise it falls back to a deterministic local sentence extractor.
3. Tavily searches the web once per extracted claim when its key is configured.
4. The app compares claim terms with returned snippets, estimates the age of the newest dated source, and shows its triage result and evidence.
5. The answer score is the average of the per-claim scores. Each live claim score combines a heuristic snippet-overlap signal (65%) and the newest available source's age (35%). If a source has no date, the freshness signal uses a neutral default and the UI states that the date is unavailable. These are prototype heuristics, not calibrated probabilities.

When Tavily is not configured, the app displays sample evidence, marks each claim as demo-only, and leaves the overall score blank. It never presents this mode as live search.

## Technologies and architecture

- **Frontend:** HTML, CSS, and browser JavaScript; no frontend framework or build step.
- **Application server:** Python 3.11+ standard library HTTP server.
- **Live web search:** Tavily Search API, optional until a key is supplied.
- **AI gateway:** optional Bifrost-compatible OpenAI chat-completions endpoint for claim extraction. No gateway is connected by default. Configure providers and routing in your own Bifrost deployment; the local extractor remains available as a fallback. See the [Bifrost documentation](https://docs.getbifrost.ai/).
- **Storage:** none. Answers are processed in the request and are not written to a database or file by the app.

## Run locally

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open http://localhost:8000. Without keys, the app runs in demo mode. Add keys to `.env` to enable the corresponding integrations.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `TAVILY_API_KEY` | Live search and evidence | unset (demo mode) |
| `BIFROST_BASE_URL` | OpenAI-compatible Bifrost API base, typically ending in `/v1` | unset (local extractor) |
| `BIFROST_API_KEY` | Bifrost virtual key | unset |
| `BIFROST_MODEL` | Model configured in the gateway | `openai/gpt-4o-mini` |
| `PORT` | HTTP port | `8000` |
| `MAX_ANSWER_CHARS` | Maximum answer size | `12000` |
| `MAX_CLAIMS` | Maximum claims searched per request | `8` |

The Bifrost adapter sends `POST {BIFROST_BASE_URL}/chat/completions` with an OpenAI-compatible request. The gateway is only used for claim extraction. The MVP does not send claims and evidence to an LLM for verdicts.

## API

`POST /api/analyze`

```json
{ "answer": "Paste an AI-generated answer here." }
```

Returns an analysis timestamp, overall score, extraction/search modes, and each claim's text, status, heuristic freshness score, rationale, and source details.

`GET /api/health` reports whether Tavily and Bifrost settings are present. It does not return credentials.

## Tests and current checks

```bash
python -m unittest discover -s tests -v
```

The tests cover local claim extraction, date handling, unsupported-result scoring, empty input validation, and no-key demo mode. GitHub Actions runs the suite on pushes to `main` and on pull requests.

## Roadmap from the Round 1 proposal

1. Add model-assisted evidence comparison and claim-level verdicts through the Bifrost gateway.
2. Score evidence recency, agreement among independent sources, and source reliability separately.
3. Weight time-sensitive claims such as prices, API limits, software versions, policies, leadership, and deadlines.
4. Evaluate stale detection, evidence relevance, latency, and cost on a labeled set of time-sensitive AI answers.
5. Consider a developer API or browser extension after the core verification flow is evaluated.

These items are planned work; the repository does not report completed benchmark results or a deployed production service.

## Deployment

### Render

1. Create a Render Web Service from this public repository.
2. Set the build command to `pip install -r requirements.txt` and the start command to `python app.py`.
3. Add `TAVILY_API_KEY` and, optionally, `BIFROST_BASE_URL`, `BIFROST_API_KEY`, and `BIFROST_MODEL` in the service environment settings.
4. Deploy and open the generated HTTPS URL.

### Docker

```bash
docker build -t claimtrace-ai .
docker run --rm -p 8000:8000 --env-file .env claimtrace-ai
```

Never commit `.env` or provider keys. `.gitignore` excludes `.env`.

## Limitations and responsible use

Search relevance is not entailment. Search may miss sources, return outdated snippets, or surface pages that do not support a claim in context. The current overlap and freshness scores are triage signals only. Source publication dates are shown only when the provider supplies them. This prototype has input-size limits but no production rate limiting or authentication; add suitable controls before exposing a deployment broadly.

## Hackathon submission details

- **Project title:** ClaimTrace AI
- **Subtitle:** Live Claim Verification & Freshness Intelligence
- **Problem statement:** Build a Stale-Answer Detector for AI Applications
- **Demo video:** intentionally not created
- **Pitch deck:** prepared separately; it is not part of this repository

