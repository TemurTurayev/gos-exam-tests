/**
 * Общий рейтинг сайта тестов — Cloudflare Worker.
 *
 *   DELETE /scores        (заголовок x-admin-token) -> очистить таблицу
 *   DELETE /scores/<slug> (заголовок x-admin-token) -> убрать участника
 *
 * Результаты хранит Durable Object: отдельный ресурс создавать не нужно,
 * хранилище появляется вместе с самим воркером.
 *
 *   GET  /scores            -> [{ name, solved, correct, updated }, …]
 *   POST /scores {name, slug, solved, correct}
 *
 * Счёт участника может только расти: заход с чистого браузера или сброс
 * прогресса не обнуляют уже заработанные баллы.
 */

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET,POST,DELETE,OPTIONS",
  "access-control-allow-headers": "content-type,x-admin-token",
  "access-control-max-age": "86400",
};

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...CORS },
  });

/** Имя проверяем так же, как на сайте: только буквы, без цифр и знаков. */
function cleanName(raw) {
  const value = String(raw || "").trim().replace(/\s+/g, " ");
  if (!/^[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʼʻ'‘’`\-\s]+$/.test(value)) return null;
  if (value.length < 2 || value.length > 30) return null;
  return value;
}

export class Board {
  constructor(state) {
    this.state = state;
  }

  async fetch(request) {
    if (request.method === "GET") {
      const all = await this.state.storage.list({ limit: 1000 });
      return json([...all.values()]);
    }

    if (request.method === "DELETE") {
      // /scores/<slug> — убрать одного участника, /scores — очистить таблицу
      const slug = new URL(request.url).pathname.replace(/^\/scores\/?/, "").trim();
      if (slug) {
        const existed = Boolean(await this.state.storage.get(slug));
        await this.state.storage.delete(slug);
        return json({ ok: true, removed: slug, existed });
      }
      await this.state.storage.deleteAll();
      return json({ ok: true, cleared: true });
    }

    if (request.method === "POST") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "bad json" }, 400);
      }

      const name = cleanName(body.name);
      const solved = Number(body.solved) || 0;
      const correct = Number(body.correct) || 0;
      if (!name || solved <= 0 || correct < 0 || correct > solved) {
        return json({ error: "bad data" }, 400);
      }

      const slug = name.toLowerCase().replace(/\s+/g, "-");
      const prev = (await this.state.storage.get(slug)) || null;
      const row = {
        name,
        solved: Math.max(solved, prev?.solved || 0),
        correct: Math.max(correct, prev?.correct || 0),
        updated: new Date().toISOString(),
      };
      await this.state.storage.put(slug, row);
      return json(row);
    }

    return json({ error: "method not allowed" }, 405);
  }
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });

    const url = new URL(request.url);
    if (!url.pathname.startsWith("/scores")) return json({ error: "not found" }, 404);

    // очистка таблицы (например, перед новым потоком) — только по секрету,
    // заданному командой: wrangler secret put ADMIN_TOKEN
    if (request.method === "DELETE") {
      const token = request.headers.get("x-admin-token");
      if (!env.ADMIN_TOKEN || token !== env.ADMIN_TOKEN) {
        return json({ error: "forbidden" }, 403);
      }
    }

    // одна общая доска на всех: адресуем объект фиксированным именем
    const id = env.BOARD.idFromName("global");
    return env.BOARD.get(id).fetch(request);
  },
};
