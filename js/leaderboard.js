// Таблица лидеров.
//
// Сайт статический, поэтому по умолчанию рейтинг собирается из профилей,
// сохранённых в этом браузере: на общем компьютере или планшете группы это
// уже даёт соревнование. Для общего рейтинга между разными устройствами
// достаточно указать адрес хранилища в config.js — код сам переключится.

const Leaderboard = (() => {
  const USERS_KEY = "gos-exam-users";      // slug -> отображаемое имя
  const remoteUrl = () =>
    (typeof window !== "undefined" && window.LEADERBOARD_URL) || null;

  function registry() {
    try {
      return JSON.parse(localStorage.getItem(USERS_KEY)) || {};
    } catch {
      return {};
    }
  }

  /** Запомнить имя, чтобы показывать его в таблице. */
  function remember(name, slug) {
    const all = registry();
    all[slug] = name;
    try { localStorage.setItem(USERS_KEY, JSON.stringify(all)); } catch { /* приватный режим */ }
  }

  /** Сводка по одному профилю из его прогресса. */
  function statsFromProgress(progress) {
    let solved = 0, correct = 0;
    for (const answers of Object.values(progress.sets || {})) {
      for (const value of Object.values(answers)) {
        solved++;
        if (value === 1) correct++;
      }
    }
    return { solved, correct };
  }

  function localRows() {
    const names = registry();
    const rows = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith("gos-exam-progress-v2:")) continue;
      const slug = key.slice("gos-exam-progress-v2:".length);
      let progress;
      try {
        progress = JSON.parse(localStorage.getItem(key)) || {};
      } catch {
        continue;
      }
      const { solved, correct } = statsFromProgress(progress);
      if (!solved) continue;
      rows.push({ name: names[slug] || slug, slug, solved, correct });
    }
    return rows;
  }

  function rank(rows) {
    return rows
      .map((r) => ({ ...r, accuracy: r.solved ? r.correct / r.solved : 0 }))
      .sort((a, b) => b.correct - a.correct || b.accuracy - a.accuracy || a.name.localeCompare(b.name));
  }

  return {
    remember,

    /** Строки рейтинга: сначала пробуем общий, иначе локальный. */
    async rows() {
      const url = remoteUrl();
      if (url) {
        try {
          const res = await fetch(url, { headers: { accept: "application/json" } });
          if (res.ok) {
            const data = await res.json();
            if (Array.isArray(data)) {
              return { scope: "global", rows: rank(data.filter((r) => r && r.name)) };
            }
          }
        } catch (err) {
          console.warn("Общий рейтинг недоступен, показываем локальный:", err);
        }
      }
      return { scope: "local", rows: rank(localRows()) };
    },

    /** Отправить свой результат в общий рейтинг (если он настроен). */
    async publish() {
      const url = remoteUrl();
      if (!url || !User.name) return;
      const progress = { sets: {} };
      try {
        progress.sets = JSON.parse(
          localStorage.getItem("gos-exam-progress-v2:" + User.slug)
        ).sets || {};
      } catch {
        return;
      }
      const { solved, correct } = statsFromProgress(progress);
      if (!solved) return;
      try {
        await fetch(url, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ name: User.name, slug: User.slug, solved, correct }),
        });
      } catch (err) {
        console.warn("Не удалось отправить результат:", err);
      }
    },
  };
})();
