// Гос экзамен — тесты. Простое SPA без сборки: hash-роутинг + fetch JSON.
// Весь пользовательский/данные-текст вставляется через textContent — innerHTML
// используется только для статичной, целиком контролируемой разметки.

const app = document.getElementById("app");
const scoreBadge = document.getElementById("scoreBadge");

let manifest = null;
const questionCache = new Map();

function el(tag, opts = {}, children = []) {
  const node = document.createElement(tag);
  if (opts.className) node.className = opts.className;
  if (opts.text !== undefined) node.textContent = opts.text;
  if (opts.href !== undefined) node.href = opts.href;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  if (opts.disabled) node.disabled = true;
  if (opts.onClick) node.addEventListener("click", opts.onClick);
  for (const c of children) if (c) node.appendChild(c);
  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

async function loadManifest() {
  if (manifest) return manifest;
  const res = await fetch("data/manifest.json");
  manifest = await res.json();
  return manifest;
}

async function loadSet(id) {
  if (questionCache.has(id)) return questionCache.get(id);
  const res = await fetch(`data/${id}.json`);
  const data = await res.json();
  questionCache.set(id, data);
  return data;
}

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ---------- Routing ----------
window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", render);

function parseHash() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [pathPart, queryPart] = raw.split("?");
  const parts = pathPart.split("/").filter(Boolean);
  const params = new URLSearchParams(queryPart || "");
  return { parts, params };
}

async function render() {
  scoreBadge.hidden = true;
  const { parts, params } = parseHash();
  clear(app);
  try {
    if (parts.length === 0) {
      await renderHome();
    } else if (parts[0] === "setup" && parts[1]) {
      await renderSetup(parts[1]);
    } else if (parts[0] === "quiz" && parts[1]) {
      await renderQuiz(parts[1], params);
    } else {
      app.appendChild(el("div", { className: "empty-state", text: "Страница не найдена." }));
      app.appendChild(el("a", { href: "#/", text: "На главную" }));
    }
  } catch (err) {
    console.error(err);
    app.appendChild(el("div", { className: "empty-state", text: "Ошибка загрузки: " + err }));
  }
}

// ---------- Home ----------
async function renderHome() {
  app.appendChild(el("div", { className: "empty-state", text: "Загрузка…" }));
  const m = await loadManifest();
  clear(app);

  const bySubject = new Map();
  for (const set of m) {
    if (!bySubject.has(set.subject)) bySubject.set(set.subject, []);
    bySubject.get(set.subject).push(set);
  }
  const totalQ = m.reduce((s, x) => s + x.count, 0);

  app.appendChild(
    el("p", {
      className: "intro",
      text: `${m.length} наборов тестов · ${totalQ.toLocaleString("ru-RU")} вопросов. Выбери набор и начни тренировку.`,
    })
  );
  app.querySelector(".intro").style.cssText = "color:var(--text-dim); margin-top:0;";

  for (const [subject, sets] of bySubject) {
    const section = el("section", { className: "subject-group" });
    section.appendChild(el("h2", { className: "subject-title", text: subject }));
    const list = el("div", { className: "set-list" });
    for (const s of sets) {
      const card = el("a", { className: "set-card", href: `#/setup/${s.id}` });
      const left = el("div", {}, [
        el("div", { className: "set-card-title", text: s.title }),
        el("div", { className: "set-card-meta", text: `${s.count} вопросов` }),
      ]);
      const pill = el("span", {
        className: `pill lang-${s.language}`,
        text: s.language.toUpperCase(),
      });
      card.appendChild(left);
      card.appendChild(pill);
      list.appendChild(card);
    }
    section.appendChild(list);
    app.appendChild(section);
  }
}

// ---------- Setup ----------
async function renderSetup(id) {
  app.appendChild(el("div", { className: "empty-state", text: "Загрузка…" }));
  const m = await loadManifest();
  const meta = m.find((x) => x.id === id);
  clear(app);

  if (!meta) {
    app.appendChild(el("div", { className: "empty-state", text: "Набор не найден." }));
    app.appendChild(el("a", { href: "#/", text: "На главную" }));
    return;
  }

  app.appendChild(el("a", { className: "back-link", href: "#/", text: "← Ко всем тестам" }));

  const card = el("div", { className: "setup-card" });
  card.appendChild(el("h2", { text: meta.title }));
  const sub = el("p", { text: `Всего вопросов в наборе: ${meta.count}` });
  sub.style.color = "var(--text-dim)";
  card.appendChild(sub);

  let count = Math.min(20, meta.count);
  let order = "shuffle";

  const counts = [10, 20, 30, meta.count].filter((v, i, arr) => v <= meta.count && arr.indexOf(v) === i);
  if (!counts.length) counts.push(meta.count);
  count = counts[0];

  const countField = el("div", { className: "field" });
  countField.appendChild(el("label", { text: "Сколько вопросов?" }));
  const countRow = el("div", { className: "chip-row" });
  const countChips = [];
  counts.forEach((c, i) => {
    const chip = el("button", {
      className: "chip" + (i === 0 ? " active" : ""),
      text: c === meta.count ? `Все (${c})` : String(c),
      attrs: { type: "button" },
      onClick: () => {
        count = c;
        countChips.forEach((b) => b.classList.remove("active"));
        chip.classList.add("active");
      },
    });
    countChips.push(chip);
    countRow.appendChild(chip);
  });
  countField.appendChild(countRow);
  card.appendChild(countField);

  const orderField = el("div", { className: "field" });
  orderField.appendChild(el("label", { text: "Порядок вопросов" }));
  const orderRow = el("div", { className: "chip-row" });
  const orderChips = [];
  [
    ["shuffle", "Случайный"],
    ["sequential", "По порядку"],
  ].forEach(([val, label], i) => {
    const chip = el("button", {
      className: "chip" + (i === 0 ? " active" : ""),
      text: label,
      attrs: { type: "button" },
      onClick: () => {
        order = val;
        orderChips.forEach((b) => b.classList.remove("active"));
        chip.classList.add("active");
      },
    });
    orderChips.push(chip);
    orderRow.appendChild(chip);
  });
  orderField.appendChild(orderRow);
  card.appendChild(orderField);

  card.appendChild(
    el("button", {
      className: "btn",
      text: "Начать тест →",
      onClick: () => {
        location.hash = `#/quiz/${id}?count=${count}&order=${order}`;
      },
    })
  );

  app.appendChild(card);
}

// ---------- Quiz ----------
async function renderQuiz(id, params) {
  app.appendChild(el("div", { className: "empty-state", text: "Загрузка вопросов…" }));
  const data = await loadSet(id);
  clear(app);

  const count = Math.min(Number(params.get("count")) || 20, data.questions.length);
  const order = params.get("order") || "shuffle";

  let pool = order === "shuffle" ? shuffle(data.questions) : data.questions.slice();
  const questions = pool.slice(0, count).map((q) => {
    const optIdx = q.options.map((_, i) => i);
    const shuffledIdx = shuffle(optIdx);
    return {
      q: q.q,
      options: shuffledIdx.map((i) => q.options[i]),
      correct: shuffledIdx.indexOf(q.correct),
    };
  });

  const state = { i: 0, answers: new Array(questions.length).fill(null), score: 0 };

  function updateScoreBadge() {
    scoreBadge.hidden = false;
    const answeredCount = state.answers.filter((a) => a !== null).length;
    scoreBadge.textContent = `${state.score} / ${answeredCount} правильно`;
  }

  function renderQuestion() {
    clear(app);
    const idx = state.i;
    const q = questions[idx];
    const answered = state.answers[idx];
    const pct = Math.round((idx / questions.length) * 100);

    app.appendChild(
      el("a", { className: "back-link", href: `#/setup/${id}`, text: "← Настройки теста" })
    );

    const progress = el("div", { className: "quiz-progress" });
    const bar = el("div", { className: "quiz-progress-bar" });
    bar.style.width = pct + "%";
    progress.appendChild(bar);
    app.appendChild(progress);

    const qCard = el("div", { className: "question-card" });
    qCard.appendChild(
      el("div", { className: "question-index", text: `Вопрос ${idx + 1} из ${questions.length}` })
    );
    qCard.appendChild(el("div", { className: "question-text", text: q.q }));

    const optList = el("div", { className: "option-list", attrs: { id: "optionList" } });
    q.options.forEach((opt, i) => {
      const btn = el("button", {
        className: "option-btn",
        text: opt,
        attrs: { type: "button", "data-i": String(i) },
      });
      optList.appendChild(btn);
    });
    qCard.appendChild(optList);
    app.appendChild(qCard);

    const actions = el("div", { className: "quiz-actions" });
    const nextBtn = el("button", {
      className: "btn secondary",
      text: idx === questions.length - 1 ? "Результаты →" : "Дальше →",
      disabled: answered === null,
      attrs: { id: "nextBtn" },
      onClick: () => {
        if (idx === questions.length - 1) renderResults();
        else {
          state.i++;
          renderQuestion();
        }
      },
    });
    actions.appendChild(nextBtn);
    app.appendChild(actions);

    if (answered !== null) markAnswered(q, answered);

    optList.addEventListener("click", (e) => {
      const btn = e.target.closest(".option-btn");
      if (!btn || state.answers[idx] !== null) return;
      const chosen = Number(btn.dataset.i);
      state.answers[idx] = chosen;
      if (chosen === q.correct) state.score++;
      markAnswered(q, chosen);
      updateScoreBadge();
      nextBtn.disabled = false;
    });

    updateScoreBadge();
  }

  function markAnswered(q, chosen) {
    document.querySelectorAll("#optionList .option-btn").forEach((b) => {
      const i = Number(b.dataset.i);
      b.disabled = true;
      if (i === q.correct) b.classList.add("correct");
      else if (i === chosen) b.classList.add("wrong");
    });
  }

  function renderResults() {
    clear(app);
    scoreBadge.hidden = true;
    const total = questions.length;
    const pct = Math.round((state.score / total) * 100);
    const wrong = questions
      .map((q, i) => ({ q, chosen: state.answers[i] }))
      .filter((x) => x.chosen !== x.q.correct);

    const card = el("div", { className: "result-card" });
    card.appendChild(el("div", { text: "Результат" }));
    card.appendChild(el("div", { className: "result-score", text: `${state.score} / ${total} (${pct}%)` }));
    const actions = el("div", { className: "result-actions" }, [
      el("a", { className: "btn secondary", href: `#/setup/${id}`, text: "Попробовать ещё раз" }),
      el("a", { className: "btn", href: "#/", text: "К списку тестов" }),
    ]);
    card.appendChild(actions);
    app.appendChild(card);

    if (wrong.length) {
      app.appendChild(el("h3", { text: `Разбор ошибок (${wrong.length})` })).style.marginTop = "28px";
      const list = el("div", { className: "review-list" });
      for (const x of wrong) {
        const item = el("div", { className: "review-item" }, [
          el("div", { className: "review-q", text: x.q.q }),
          el("div", {
            className: "review-your",
            text: "Твой ответ: " + (x.chosen === null ? "—" : x.q.options[x.chosen]),
          }),
          el("div", { className: "review-correct", text: "Правильный: " + x.q.options[x.q.correct] }),
        ]);
        list.appendChild(item);
      }
      app.appendChild(list);
    } else {
      const ok = el("p", { text: "Все ответы верны! 🎉" });
      ok.style.cssText = "text-align:center; color: var(--correct); font-weight:600; margin-top:20px;";
      app.appendChild(ok);
    }
  }

  renderQuestion();
}
