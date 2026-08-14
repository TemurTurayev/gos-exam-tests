// Загрузка банков вопросов. В офлайн-сборке данные уже вшиты в страницу
// (window.EMBEDDED_DATA), поэтому сеть не нужна и файл работает с диска.

const Data = (() => {
  const cache = new Map();
  let manifest = null;

  const embedded = () => (typeof window !== "undefined" ? window.EMBEDDED_DATA : null);

  async function loadManifest() {
    if (manifest) return manifest;
    const emb = embedded();
    manifest = emb ? emb.manifest : await (await fetch("data/manifest.json")).json();
    return manifest;
  }

  async function loadSet(id) {
    if (cache.has(id)) return cache.get(id);
    const emb = embedded();
    const data = emb ? emb.sets[id] : await (await fetch(`data/${id}.json`)).json();
    cache.set(id, data);
    return data;
  }

  /** Все наборы разом — нужно для общего пула. */
  async function loadAll() {
    const m = await loadManifest();
    return Promise.all(m.map((s) => loadSet(s.id)));
  }

  /**
   * Собирает вопросы для прохождения.
   * scope: id набора или "pool" (все наборы вперемешку).
   * filter: "all" | "unsolved" | "wrong"
   */
  async function buildQuiz({ scope, count, order, filter }) {
    const sets = scope === "pool" ? await loadAll() : [await loadSet(scope)];

    let items = [];
    for (const set of sets) {
      const answers = Progress.forSet(set.id);
      set.questions.forEach((q, index) => {
        const state = answers[index];
        if (filter === "unsolved" && state !== undefined) return;
        if (filter === "wrong" && state !== 0) return;
        items.push({ setId: set.id, setTitle: set.title, index, q });
      });
    }

    if (order !== "sequential") items = shuffle(items);
    items = items.slice(0, Math.min(count, items.length));

    // варианты тоже перемешиваем, иначе правильный часто стоит первым
    return items.map((item) => {
      const order = shuffle(item.q.options.map((_, i) => i));
      return {
        setId: item.setId,
        setTitle: item.setTitle,
        index: item.index,
        text: item.q.q,
        options: order.map((i) => item.q.options[i]),
        correct: order
          .map((orig, pos) => (item.q.correct.includes(orig) ? pos : -1))
          .filter((pos) => pos >= 0)
          .sort((a, b) => a - b),
      };
    });
  }

  /** Сколько вопросов доступно при таком фильтре. */
  async function countAvailable(scope, filter) {
    const sets = scope === "pool" ? await loadAll() : [await loadSet(scope)];
    let n = 0;
    for (const set of sets) {
      const answers = Progress.forSet(set.id);
      set.questions.forEach((_, index) => {
        const state = answers[index];
        if (filter === "unsolved" && state !== undefined) return;
        if (filter === "wrong" && state !== 0) return;
        n++;
      });
    }
    return n;
  }

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  return { loadManifest, loadSet, loadAll, buildQuiz, countAvailable, shuffle };
})();
