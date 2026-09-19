import {createServer} from 'node:http';
import {DatabaseSync} from 'node:sqlite';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import app from './backend/api/app.mjs';
import {adapter} from './backend/state/database.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 8765);
const dbFile = process.env.COGNIX_DB || path.join(root, '.local', 'cognix.sqlite');
const datasetDir = process.env.DATASET_DIR || path.join(root, 'backend', 'dataset');

fs.mkdirSync(path.dirname(dbFile), {recursive: true});
const sqlite = new DatabaseSync(dbFile);
sqlite.exec('PRAGMA journal_mode = WAL');
sqlite.exec(fs.readFileSync(path.join(root, 'backend/db/migrations/001_initial.sql'), 'utf8'));

const env = {
  DB: adapter(sqlite),
  LOCAL: true,
  DATASET_DIR: datasetDir,
  OPENAI_API_KEY: process.env.OPENAI_API_KEY || '',
  OPENAI_MODEL: process.env.OPENAI_MODEL || 'gpt-4.1-mini'
};

const staticFiles = {
  '/': ['frontend/index.html', 'text/html; charset=utf-8'],
  '/styles.css': ['frontend/styles.css', 'text/css; charset=utf-8'],
  '/app.js': ['frontend/app.js', 'text/javascript; charset=utf-8']
};

function serveStatic(url, response) {
  const entry = staticFiles[url];
  if (!entry) return false;
  const [relative, type] = entry;
  const content = fs.readFileSync(path.join(root, relative));
  response.writeHead(200, {
    'Content-Type': type,
    'Cache-Control': url === '/' ? 'no-cache' : 'public, max-age=3600',
    'X-Content-Type-Options': 'nosniff'
  });
  response.end(content);
  return true;
}

const server = createServer(async (request, response) => {
  try {
    if (request.url && !request.url.startsWith('/api/') && request.url !== '/health') {
      if (serveStatic(new URL(request.url, `http://${request.headers.host || 'localhost'}`).pathname, response)) return;
    }

    const chunks = [];
    let size = 0;
    for await (const chunk of request) {
      size += chunk.length;
      if (size > 15000) {
        response.writeHead(413);
        response.end('Request too large');
        return;
      }
      chunks.push(chunk);
    }

    const body = Buffer.concat(chunks);
    const url = `http://127.0.0.1:${port}${request.url}`;
    const webRequest = new Request(url, {
      method: request.method,
      headers: request.headers,
      ...(body.length ? {body} : {})
    });

    const result = await app.fetch(webRequest, env);
    response.writeHead(result.status, Object.fromEntries(result.headers));
    response.end(Buffer.from(await result.arrayBuffer()));
  } catch (error) {
    console.error(error);
    response.writeHead(500, {'Content-Type': 'application/json'});
    response.end(JSON.stringify({error: 'Server error.'}));
  }
});

server.listen(port, '127.0.0.1', () => {
  console.log(`COGNIX running at http://127.0.0.1:${port}`);
});
