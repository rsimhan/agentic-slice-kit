# Architecture

## Request flow

Browser → HTTP API → diagnostic controller → retrieval/model services → persistent profile.

### Controller

The controller is authoritative for:

- state transitions
- attempt and revision limits
- allowed hypotheses
- evidence storage
- student confirmation
- profile updates

### LLM

The model is used only for bounded, structured suggestions and interpretation. Responses are schema-checked and constrained to the currently permitted checks.

### Retrieval

`backend/retrieval/index.mjs` loads the JSON corpus from `backend/dataset/` and returns relevant documents. The dataset directory can remain empty during development.

### Persistence

Student profiles are stored as JSON in SQLite with optimistic revision checks and a short write lease to prevent concurrent updates from overwriting each other.
