import fs from 'node:fs/promises';
import path from 'node:path';

const SUPPORTED = new Set(['.json']);

async function filesIn(dir) {
  try {
    const entries = await fs.readdir(dir, {withFileTypes: true});
    const nested = await Promise.all(entries.map(async entry => {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) return filesIn(full);
      return SUPPORTED.has(path.extname(entry.name).toLowerCase()) ? [full] : [];
    }));
    return nested.flat();
  } catch {
    return [];
  }
}

function score(doc, terms) {
  const haystack = `${doc.title ?? ''} ${doc.topic ?? ''} ${doc.content ?? ''} ${(doc.tags ?? []).join(' ')}`.toLowerCase();
  return terms.reduce((total, term) => total + (haystack.includes(term) ? 1 : 0), 0);
}

export async function retrieve(query, {datasetDir, limit = 5} = {}) {
  if (!datasetDir) return [];
  const files = await filesIn(datasetDir);
  const terms = String(query).toLowerCase().split(/[^a-z0-9]+/).filter(t => t.length > 2);
  const documents = [];

  for (const file of files) {
    try {
      const raw = JSON.parse(await fs.readFile(file, 'utf8'));
      const items = Array.isArray(raw) ? raw : [raw];
      for (const doc of items) {
        if (!doc || typeof doc !== 'object' || typeof doc.content !== 'string') continue;
        const relevance = score(doc, terms);
        if (relevance > 0) documents.push({
          id: doc.id ?? path.basename(file),
          title: doc.title ?? 'Untitled',
          topic: doc.topic ?? '',
          content: doc.content,
          relevance
        });
      }
    } catch {
      // Ignore malformed dataset entries; one bad document should not stop diagnosis.
    }
  }

  return documents
    .sort((a, b) => b.relevance - a.relevance)
    .slice(0, limit);
}
