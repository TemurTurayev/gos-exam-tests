// Загрузка банков вопросов. В офлайн-сборке данные вшиты в страницу
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

  /** Наборы выбранного языка ("all" — любые). */
  async function setsFor(scope, testLang) {
    const m = await loadManifest();
    if (scope !== "pool") return [await loadSet(scope)];
    const wanted = m.filter((s) => testLang === "all" || s.language === testLang);
    return Promise.all(wanted.map((s) => loadSet(s.id)));
  }

  function passesTrust(tag, trust) {
    if (trust === "strict") return TRUSTED_TAGS.includes(tag);
    if (trust === "flagged") return !TRUSTED_TAGS.includes(tag);
    return true;
  }

  function passesProgress(state, filter) {
    if (filter === "unsolved") return state === undefined;
    if (filter === "wrong") return state === 0;
    return true;
  }

  /** Плоский список вопросов, подходящих под фильтры. */
  async function collect({ scope, filter, trust, testLang }) {
    const sets = await setsFor(scope, testLang);
    const items = [];
    for (const set of sets) {
      const answers = Progress.forSet(set.id);
      set.questions.forEach((q, index) => {
        if (!passesProgress(answers[index], filter)) return;
        if (!passesTrust(q.tag, trust)) return;
        items.push({ setId: set.id, setTitle: set.title, setTitleUz: set.title_uz, index, q });
      });
    }
    return items;
  }

  /** Готовит вопросы к прохождению: порядок, перемешанные варианты. */
  async function buildQuiz({ scope, count, order, filter, trust, testLang }) {
    let items = await collect({ scope, filter, trust, testLang });
    if (order !== "sequential") items = shuffle(items);
    items = items.slice(0, Math.min(count, items.length));

    return items.map((item) => {
      const mix = shuffle(item.q.options.map((_, i) => i));
      return {
        setId: item.setId,
        setTitle: (I18N.lang === "uz" && item.setTitleUz) || item.setTitle,
        index: item.index,
        text: item.q.q,
        tag: item.q.tag,
        options: mix.map((i) => item.q.options[i]),
        correct: mix
          .map((orig, pos) => (item.q.correct.includes(orig) ? pos : -1))
          .filter((pos) => pos >= 0)
          .sort((a, b) => a - b),
      };
    });
  }

  async function countAvailable(opts) {
    return (await collect(opts)).length;
  }

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  return { loadManifest, loadSet, buildQuiz, countAvailable, shuffle };
})();
