import {
  start, answer, confirmDiagnosis, demoStep, current, stop,
  dashboard, H, MODULES, DEFAULT_QUESTION, DEFAULT_ATTEMPT
} from '../agent/controller.mjs';
import {load, acquire, persist, release} from '../state/store.mjs';

const JSON_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
  'X-Content-Type-Options': 'nosniff'
};

const json = (data, status = 200, extra = {}) =>
  new Response(JSON.stringify(data), {status, headers: {...JSON_HEADERS, ...extra}});

function identity(request) {
  const value = request.headers.get('Cookie')
    ?.match(/(?:^|; )cognix_session=([a-f0-9-]{36})(?:;|$)/)?.[1];
  return {id: value || crypto.randomUUID(), fresh: !value};
}

function packet(profile, env) {
  return {
    profile,
    dashboard: dashboard(profile),
    run: current(profile),
    catalog: H,
    modules: MODULES,
    defaults: {question: DEFAULT_QUESTION, attempt: DEFAULT_ATTEMPT},
    service: {
      configured: Boolean(env.OPENAI_API_KEY && env.OPENAI_MODEL),
      model: env.OPENAI_MODEL || null,
      storage: env.LOCAL ? 'Local SQLite' : 'Persistent database'
    }
  };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/health') return json({ok: true});

    if (!url.pathname.startsWith('/api/')) return json({error: 'Not found'}, 404);

    const who = identity(request);
    const space = url.searchParams.get('profile') === 'demo' ? 'demo' : 'practice';
    const id = `${who.id}:${space}`;
    const cookie = who.fresh
      ? {'Set-Cookie': `cognix_session=${who.id}; HttpOnly; SameSite=Lax; Path=/; Max-Age=31536000`}
      : {};

    let lease = null;

    try {
      const profile = await load(env.DB, id, space === 'demo' ? 'Demo Student' : 'Practice Student');

      if (request.method === 'GET' && url.pathname === '/api/profile') {
        return json(packet(profile, env), 200, cookie);
      }

      if (request.method !== 'POST' || url.pathname !== '/api/action') {
        return json({error: 'Not found'}, 404, cookie);
      }

      const origin = request.headers.get('Origin');
      if (origin && origin !== url.origin) {
        return json({error: 'Request origin not allowed.'}, 403, cookie);
      }

      if (!request.headers.get('Content-Type')?.startsWith('application/json')) {
        return json({error: 'JSON request required.'}, 415, cookie);
      }

      const raw = await request.text();
      if (raw.length > 12000) return json({error: 'Request is too large.'}, 413, cookie);

      let body;
      try {
        body = JSON.parse(raw);
      } catch {
        return json({error: 'Invalid request JSON.'}, 400, cookie);
      }

      if (!body || typeof body !== 'object' || Array.isArray(body)) {
        return json({error: 'Invalid request.'}, 400, cookie);
      }

      if (typeof body.request_id !== 'string' || body.request_id.length > 80) {
        return json({error: 'A request ID is required.'}, 400, cookie);
      }

      if (profile.processed?.includes(body.request_id)) {
        return json(packet(profile, env), 200, cookie);
      }

      if (body.revision !== profile.revision) {
        return json({error: 'The profile changed. Reload the latest session.', reload: true}, 409, cookie);
      }

      lease = await acquire(env.DB, id, profile.revision);
      if (!lease) {
        return json({error: 'Another request is being processed. Reload the session.', reload: true}, 409, cookie);
      }

      if (body.kind === 'start') {
        if (body.mode === 'demo' && space !== 'demo') throw new Error('Use the demo profile for demo mode.');
        await start(profile, env, body);
      } else if (body.kind === 'answer') {
        await answer(profile, env, body);
      } else if (body.kind === 'confirm') {
        await confirmDiagnosis(profile, env, body.value);
      } else if (body.kind === 'stop') {
        const run = current(profile);
        if (!run || !['WAIT', 'WAIT_FOR_STUDENT'].includes(run.state)) throw new Error('No active investigation.');
        stop(run, 'stopped', 'The investigation was stopped by the student.');
      } else if (body.kind === 'demo_start') {
        if (space !== 'demo') throw new Error('Demo profile required.');
        if (current(profile) && current(profile).state !== 'FINISH') stop(current(profile), 'stopped', 'Previous demo session closed.');
        await start(profile, env, {module: 'exam', mode: 'demo', ignoreMemory: true, demo_encounter: 1});
      } else if (body.kind === 'demo_step') {
        if (space !== 'demo') throw new Error('Demo profile required.');
        await demoStep(profile, env);
      } else if (body.kind === 'task') {
        const title = String(body.title || '').trim();
        if (!title || title.length > 100 || !/^\d{4}-\d{2}-\d{2}$/.test(body.due || '') || !Number.isFinite(Date.parse(body.due))) {
          throw new Error('Enter a task and a valid date.');
        }
        profile.tasks.push({id: crypto.randomUUID(), title, due: body.due, done: false});
      } else if (body.kind === 'task_done') {
        const task = profile.tasks.find(item => item.id === body.task_id);
        if (!task) throw new Error('Task not found.');
        task.done = !task.done;
      } else if (body.kind === 'feedback') {
        const intervention = profile.interventions.find(item => item.id === body.intervention_id);
        if (!intervention || !['Helped', 'Did not help', 'Not tried'].includes(body.value)) {
          throw new Error('Invalid intervention feedback.');
        }
        intervention.outcome = body.value;
        intervention.feedback_at = new Date().toISOString();
      } else {
        throw new Error('Unknown action.');
      }

      profile.processed = [...(profile.processed || []), body.request_id].slice(-40);
      await persist(env.DB, profile, lease);
      lease = null;
      return json(packet(profile, env), 200, cookie);
    } catch (error) {
      if (lease) {
        try { await release(env.DB, id, lease); } catch {}
      }
      const expected = /question|attempt|Choose|Enter|Invalid|current|session|limit|already|mode|profile required|positive mass|MVP supports|Unknown action|Task not found|shorten|valid date/i.test(error.message);
      if (!expected) console.error('Request failed:', url.pathname, error.message);
      return json(
        {error: expected ? error.message : 'The answer has not been confirmed as saved. Please retry.', reload: !expected},
        expected ? 400 : 503,
        cookie
      );
    }
  }
};
