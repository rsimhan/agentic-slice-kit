# COGNIX Diagnostic Agent

A small, evidence-driven academic diagnostic backend with a separate browser frontend.

## Structure

```text
frontend/                 Browser UI
backend/
  api/                    HTTP application
  agent/                  Diagnostic state machine and domain checks
  llm/                    Model client and response validation
  retrieval/              Dataset loader and relevance filtering
  state/                  Persistent profile state
  db/migrations/          SQLite schema
  dataset/                Runtime knowledge source; intentionally empty
  integrations/api/       Extension point for external API providers
tests/                    Unit and integration coverage
docs/                     Architecture and dataset notes
server.mjs                Local development server
```

## Run

Requires Node.js 22.13+.

```bash
cp .env.example .env
npm start
```

Open `http://127.0.0.1:8765`.

The application runs without an API key using the deterministic diagnostic engine. Set `OPENAI_API_KEY` and `OPENAI_MODEL` to enable model-assisted hypothesis selection and answer interpretation.

## Dataset

`backend/dataset/` is deliberately empty in the repository.

The retrieval layer reads JSON knowledge documents from that directory at runtime. The LLM receives the retrieved documents as context; it does not read the filesystem directly.

Expected document shape:

```json
{
  "id": "physics-newtons-second-law",
  "title": "Newton's Second Law",
  "topic": "Force and acceleration",
  "tags": ["force", "mass", "acceleration"],
  "content": "Knowledge content used as retrieval context."
}
```

Multiple documents can be stored in one JSON array or as separate JSON files. Malformed files are ignored rather than stopping a diagnostic session.

## Design

The model proposes within an allowed set of hypotheses and checks. The controller owns state transitions, evidence classification, revision limits, confirmation, and persistence. A model response cannot directly mutate diagnostic state.

The dataset is an additional knowledge source, not a replacement for the reviewed diagnostic checks.

## Test

```bash
npm test
```
