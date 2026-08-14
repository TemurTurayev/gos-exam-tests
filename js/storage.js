// Прогресс пользователя: какие вопросы уже решены и с каким результатом.
// Хранится в localStorage браузера, ключ — id набора, значение — карта
// «индекс вопроса -> 1 (верно) | 0 (ошибка)».

const Progress = (() => {
  const KEY = "gos-exam-progress-v1";
  let cache = null;

  function load() {
    if (cache) return cache;
    try {
      cache = JSON.parse(localStorage.getItem(KEY)) || { sets: {} };
    } catch {
      cache = { sets: {} };
    }
    if (!cache.sets) cache.sets = {};
    return cache;
  }

  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(load()));
    } catch (err) {
      console.warn("Не удалось сохранить прогресс:", err);
    }
  }

  return {
    /** Отметить ответ на вопрос набора. */
    mark(setId, index, isCorrect) {
      const data = load();
      if (!data.sets[setId]) data.sets[setId] = {};
      data.sets[setId][index] = isCorrect ? 1 : 0;
      save();
    },

    /** Карта ответов набора: { "12": 1, "13": 0 }. */
    forSet(setId) {
      return load().sets[setId] || {};
    },

    /** Сводка по набору: решено, верно, ошибок. */
    stats(setId, total) {
      const answers = this.forSet(setId);
      const keys = Object.keys(answers);
      const right = keys.filter((k) => answers[k] === 1).length;
      return { done: keys.length, right, wrong: keys.length - right, total };
    },

    /** Сводка по всем наборам сразу. */
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

    /** Сбросить прогресс набора либо, без аргумента, весь прогресс. */
    reset(setId) {
      const data = load();
      if (setId) delete data.sets[setId];
      else data.sets = {};
      save();
    },
  };
})();
