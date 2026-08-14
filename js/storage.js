// Профиль пользователя и его прогресс.
// Имя вводится при входе; прогресс каждого имени хранится отдельным ключом
// localStorage, поэтому одним устройством могут пользоваться несколько человек.

const User = (() => {
  const KEY = "gos-exam-user";

  // буквы латиницы и кириллицы, пробел, дефис и апостроф во всех начертаниях,
  // которыми пишут узбекские имена: O‘tkir, G‘ulom, Sayyora-Xon
  const ALLOWED = /^[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʼʻ'‘’`\-\s]+$/;
  const LETTER = /[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ]/g;

  return {
    /** Проверка имени. Возвращает {ok, value} либо {ok:false, error}. */
    validate(raw) {
      const value = (raw || "").trim().replace(/\s+/g, " ");
      if (!value) return { ok: false, error: "errEmpty" };
      if (!ALLOWED.test(value)) return { ok: false, error: "errChars" };
      // хотя бы одно слово должно быть настоящим словом, а не одной буквой
      const words = value.split(" ").map((w) => (w.match(LETTER) || []).length);
      if (!words.some((n) => n > 0)) return { ok: false, error: "errLetters" };
      if (Math.max(...words) < 2) return { ok: false, error: "errShort" };
      if (value.length > 30) return { ok: false, error: "errLong" };
      // приводим к виду «Temur Turayev»
      const pretty = value
        .split(" ")
        .map((w) => w.charAt(0).toLocaleUpperCase() + w.slice(1))
        .join(" ");
      return { ok: true, value: pretty };
    },

    get name() {
      try { return localStorage.getItem(KEY) || ""; } catch { return ""; }
    },

    set(name) {
      try { localStorage.setItem(KEY, name); } catch { /* приватный режим */ }
    },

    clear() {
      try { localStorage.removeItem(KEY); } catch { /* приватный режим */ }
    },

    /** Ключ хранения прогресса для текущего имени. */
    get slug() {
      return this.name.toLocaleLowerCase().replace(/\s+/g, "-");
    },
  };
})();

const Progress = (() => {
  const PREFIX = "gos-exam-progress-v2:";
  let cache = null;
  let cacheKey = null;

  function storageKey() {
    return PREFIX + (User.slug || "guest");
  }

  function load() {
    const k = storageKey();
    if (cache && cacheKey === k) return cache;
    try {
      cache = JSON.parse(localStorage.getItem(k)) || { sets: {} };
    } catch {
      cache = { sets: {} };
    }
    if (!cache.sets) cache.sets = {};
    cacheKey = k;
    return cache;
  }

  function save() {
    try {
      localStorage.setItem(storageKey(), JSON.stringify(load()));
    } catch (err) {
      console.warn("Не удалось сохранить прогресс:", err);
    }
  }

  return {
    /** Сбросить кэш при смене пользователя. */
    invalidate() {
      cache = null;
      cacheKey = null;
    },

    mark(setId, index, isCorrect) {
      const data = load();
      if (!data.sets[setId]) data.sets[setId] = {};
      data.sets[setId][index] = isCorrect ? 1 : 0;
      save();
    },

    forSet(setId) {
      return load().sets[setId] || {};
    },

    stats(setId, total) {
      const answers = this.forSet(setId);
      const keys = Object.keys(answers);
      const right = keys.filter((k) => answers[k] === 1).length;
      return { done: keys.length, right, wrong: keys.length - right, total };
    },

    totals(manifest) {
      return manifest.reduce(
        (acc, set) => {
          const s = this.stats(set.id, set.count);
          acc.done += s.done;
          acc.right += s.right;
          acc.total += set.count;
          return acc;
        },
        { done: 0, right: 0, total: 0 }
      );
    },

    reset(setId) {
      const data = load();
      if (setId) delete data.sets[setId];
      else data.sets = {};
      save();
    },
  };
})();
