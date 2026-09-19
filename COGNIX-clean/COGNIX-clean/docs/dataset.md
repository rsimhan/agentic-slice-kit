# Dataset contract

Keep the dataset directory empty until the subject/topic corpus is ready.

At runtime, the retrieval service scans `backend/dataset/` for JSON files. Each document should contain:

- `id`
- `title`
- `topic`
- `tags` (optional array)
- `content`

Retrieval performs lightweight lexical matching and returns the most relevant documents to the LLM. This keeps the knowledge source independent from the diagnostic controller and makes the corpus replaceable without changing application logic.
