/**
 * Общий рейтинг для сайта тестов — Cloudflare Worker.
 *
 * Разворачивается бесплатно и хранит результаты в KV.
 *
 *   npm create cloudflare@latest gos-exam-board
 *   # положить этот файл в src/index.js
 *   npx wrangler kv namespace create SCORES
 *   # прописать выданный id в wrangler.toml:
 *   #   [[kv_namespaces]]
 *   #   binding = "SCORES"
 *   #   id = "..."
 *   npx wrangler deploy
 *
 * Затем адрес воркера вписать в config.js сайта:
 *   window.LEADERBOARD_URL = "https://gos-exam-board.<ваш>.workers.dev/scores";
 */

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET,POST,OPTIONS",
  "access-control-allow-headers": "content-type",
};

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...CORS },
  });

/** Имя: только буквы, как и на сайте — чтобы в таблицу не писали мусор. */
function cleanName(raw) {
  const value = String(raw || "").trim().replace(/\s+/g, " ");
  if (!/^[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʼʻ'‘’`\-\s]+$/.test(value)) return null;
  if (value.length < 2 || value.length > 30) return null;
  return value;
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });

    const url = new URL(request.url);
    if (!url.pathname.startsWith("/scores")) return json({ error: "not found" }, 404);

    if (request.method === "GET") {
      const list = await env.SCORES.list({ limit: 1000 });
      const rows = await Promise.all(
        list.keys.map(async (k) => {
          try {
            return JSON.parse(await env.SCORES.get(k.name));
          } catch {
            return null;
          }
        })
      );
      return json(rows.filter(Boolean));
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
      if (!name || solved <= 0 || correct > solved) return json({ error: "bad data" }, 400);

      const slug = name.toLowerCase().replace(/\s+/g, "-");
      const prev = JSON.parse((await env.SCORES.get(slug)) || "null");
      // результат может только расти: так перезаход с чистым браузером
      // не обнулит уже заработанные баллы
      const row = {
        name,
        solved: Math.max(solved, prev?.solved || 0),
        correct: Math.max(correct, prev?.correct || 0),
        updated: new Date().toISOString(),
      };
      await env.SCORES.put(slug, JSON.stringify(row));
      return json(row);
    }

    return json({ error: "method not allowed" }, 405);
  },
};
