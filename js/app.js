// Экраны приложения и роутинг. Состояния: главная -> настройка -> тест -> итоги.

const app = document.getElementById("app");
const badge = document.getElementById("scoreBadge");

const FILTERS = [
  { value: "all", label: "Все вопросы" },
  { value: "unsolved", label: "Только нерешённые" },
  { value: "wrong", label: "Работа над ошибками" },
];

// ------------------------------------------------------------------ роутинг --
function parseHash() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, query] = raw.split("?");
  return { parts: path.split("/").filter(Boolean), params: new URLSearchParams(query || "") };
}

async function render() {
  badge.hidden = true;
  clear(app);
  const { parts, params } = parseHash();
  try {
    if (!parts.length) await renderHome();
    else if (parts[0] === "setup" && parts[1]) await renderSetup(parts[1]);
    else if (parts[0] === "quiz" && parts[1]) await renderQuiz(parts[1], params);
    else notFound();
  } catch (err) {
    console.error(err);
    clear(app);
    app.appendChild(el("div", { className: "empty-state", text: "Ошибка загрузки: " + err.message }));
  }
}

function notFound() {
  app.appendChild(el("div", { className: "empty-state" }, [
    el("p", { text: "Страница не найдена" }),
    el("a", { className: "btn", href: "#/", text: "На главную" }),
  ]));
}

function loading(msg = "Загрузка…") {
  clear(app);
  app.appendChild(el("div", { className: "empty-state", text: msg }));
}

// ----------------------------------------------------------------- главная --
async function renderHome() {
  loading();
  const manifest = await Data.loadManifest();
  clear(app);

  const totals = Progress.totals(manifest);
  const pct = totals.total ? Math.round((totals.done / totals.total) * 100) : 0;
  const accuracy = totals.done ? Math.round((totals.right / totals.done) * 100) : 0;

  // шапка с общим прогрессом
  const hero = el("section", { className: "hero" }, [
    progressRing(pct, `${pct}%`, "пройдено"),
    el("div", { className: "hero-text" }, [
      el("h1", { text: "Подготовка к госэкзамену" }),
      el("p", {
        className: "hero-sub",
        text: `${manifest.length} наборов · ${totals.total.toLocaleString("ru-RU")} вопросов`,
      }),
      el("div", { className: "hero-stats" }, [
        statChip("Решено", `${totals.done.toLocaleString("ru-RU")}`),
        statChip("Правильно", totals.done ? `${accuracy}%` : "—"),
        statChip("Осталось", `${(totals.total - totals.done).toLocaleString("ru-RU")}`),
      ]),
    ]),
  ]);
  app.appendChild(hero);

  // общий пул
  const poolCard = el("a", { className: "pool-card", href: "#/setup/pool" }, [
    el("div", { className: "pool-icon", text: "🎲" }),
    el("div", { className: "pool-body" }, [
      el("div", { className: "pool-title", text: "Общий пул" }),
      el("div", {
        className: "pool-sub",
        text: "Все предметы вперемешку. Сайт помнит, что уже решено, и может выдавать только новые вопросы.",
      }),
    ]),
    el("div", { className: "pool-go", text: "→" }),
  ]);
  app.appendChild(poolCard);

  if (totals.done) {
    app.appendChild(el("div", { className: "row-actions" }, [
      el("button", {
        className: "btn ghost small",
        text: "Сбросить весь прогресс",
        onClick: () => {
          if (confirm("Удалить статистику по всем тестам?")) {
            Progress.reset();
            render();
          }
        },
      }),
    ]));
  }

  // наборы по предметам
  const bySubject = new Map();
  for (const set of manifest) {
    if (!bySubject.has(set.subject)) bySubject.set(set.subject, []);
    bySubject.get(set.subject).push(set);
  }

  for (const [subject, sets] of bySubject) {
    const section = el("section", { className: "subject-group" });
    section.appendChild(el("h2", { className: "subject-title", text: subject }));
    const list = el("div", { className: "set-list" });
    for (const set of sets) list.appendChild(setCard(set));
    section.appendChild(list);
    app.appendChild(section);
  }
}

function statChip(label, value) {
  return el("div", { className: "stat-chip" }, [
    el("span", { className: "stat-value", text: value }),
    el("span", { className: "stat-label", text: label }),
  ]);
}

function setCard(set) {
  const s = Progress.stats(set.id, set.count);
  const card = el("a", { className: "set-card", href: `#/setup/${set.id}` });

  const head = el("div", { className: "set-head" }, [
    el("div", { className: "set-title", text: set.title }),
    el("span", { className: `pill lang-${set.language}`, text: set.language.toUpperCase() }),
  ]);

  const meta = el("div", { className: "set-meta" }, [
    el("span", { text: `${set.count} вопросов` }),
    el("span", {
      className: s.done ? "set-done" : "set-done muted",
      text: s.done ? `решено ${s.done} · верно ${Math.round((s.right / s.done) * 100)}%` : "не начат",
    }),
  ]);

  card.appendChild(head);
  card.appendChild(meta);
  card.appendChild(progressBar(s.right, s.wrong, set.count));
  return card;
}

// -------------------------------------------------------------- настройка --
async function renderSetup(scope) {
  loading();
  const manifest = await Data.loadManifest();
  const isPool = scope === "pool";
  const meta = isPool ? null : manifest.find((m) => m.id === scope);
  if (!isPool && !meta) return notFound();

  const total = isPool ? manifest.reduce((s, m) => s + m.count, 0) : meta.count;
  const title = isPool ? "Общий пул" : meta.title;
  clear(app);

  app.appendChild(el("a", { className: "back-link", href: "#/", text: "← Ко всем тестам" }));

  const card = el("div", { className: "setup-card" });
  card.appendChild(el("h2", { text: title }));

  const stats = isPool
    ? Progress.totals(manifest)
    : Progress.stats(scope, total);
  card.appendChild(el("p", {
    className: "setup-sub",
    text: `${total.toLocaleString("ru-RU")} вопросов · решено ${stats.done.toLocaleString("ru-RU")}`,
  }));

  // фильтр
  let filter = "all";
  const available = el("p", { className: "available-note", text: "" });
  const filterGroup = chipGroup(FILTERS, "all", async (value) => {
    filter = value;
    await refreshAvailable();
  });
  card.appendChild(field("Какие вопросы показывать", filterGroup.row));
  card.appendChild(available);

  // количество
  let count = 20;
  const countGroup = chipGroup(
    [10, 20, 30, 50, 100].map((n) => ({ value: n, label: String(n) })).concat([{ value: 0, label: "Все" }]),
    20,
    (value) => { count = value; }
  );
  card.appendChild(field("Сколько вопросов за раз", countGroup.row));

  // порядок
  let order = "shuffle";
  const orderGroup = chipGroup(
    [{ value: "shuffle", label: "Вперемешку" }, { value: "sequential", label: "По порядку" }],
    "shuffle",
    (value) => { order = value; }
  );
  card.appendChild(field("Порядок", orderGroup.row));

  const startBtn = el("button", {
    className: "btn big",
    text: "Начать тест →",
    onClick: () => {
      const n = count === 0 ? 99999 : count;
      location.hash = `#/quiz/${scope}?count=${n}&order=${order}&filter=${filter}`;
    },
  });
  card.appendChild(startBtn);

  if (!isPool && stats.done) {
    card.appendChild(el("button", {
      className: "btn ghost small",
      text: "Сбросить прогресс этого набора",
      onClick: () => {
        if (confirm("Удалить статистику этого набора?")) {
          Progress.reset(scope);
          renderSetup(scope);
        }
      },
    }));
  }

  app.appendChild(card);

  async function refreshAvailable() {
    const n = await Data.countAvailable(scope, filter);
    available.textContent =
      filter === "all" ? "" : `Доступно по этому фильтру: ${n.toLocaleString("ru-RU")}`;
    startBtn.disabled = n === 0;
    if (n === 0) available.textContent = "По этому фильтру вопросов не осталось 🎉";
  }
  refreshAvailable();
}

function field(labelText, control) {
  return el("div", { className: "field" }, [el("label", { text: labelText }), control]);
}

// ------------------------------------------------------------------- тест --
async function renderQuiz(scope, params) {
  loading("Готовим вопросы…");
  const questions = await Data.buildQuiz({
    scope,
    count: Number(params.get("count")) || 20,
    order: params.get("order") || "shuffle",
    filter: params.get("filter") || "all",
  });
  clear(app);

  if (!questions.length) {
    app.appendChild(el("div", { className: "empty-state" }, [
      el("p", { text: "Для выбранного фильтра вопросов не нашлось." }),
      el("a", { className: "btn", href: `#/setup/${scope}`, text: "Изменить настройки" }),
    ]));
    return;
  }

  const state = { i: 0, answers: new Array(questions.length).fill(null), score: 0 };

  const onKey = (e) => {
    const q = questions[state.i];
    if (e.key >= "1" && e.key <= "9") {
      const idx = Number(e.key) - 1;
      const btn = app.querySelector(`.option-btn[data-i="${idx}"]`);
      if (btn && !btn.disabled) btn.click();
    } else if (e.key === "Enter") {
      const next = document.getElementById("primaryBtn");
      if (next && !next.disabled) next.click();
    }
  };
  document.addEventListener("keydown", onKey);
  window.addEventListener("hashchange", () => document.removeEventListener("keydown", onKey), { once: true });

  drawQuestion();

  function updateBadge() {
    const answered = state.answers.filter((a) => a !== null).length;
    badge.hidden = answered === 0;          // до первого ответа счёт не нужен
    if (!answered) return;
    badge.textContent = `${state.score} / ${answered}`;
    badge.className = "score-badge" + (answered && state.score / answered < 0.6 ? " low" : "");
  }

  function drawQuestion() {
    clear(app);
    const idx = state.i;
    const q = questions[idx];
    const multi = q.correct.length > 1;
    const answered = state.answers[idx];
    const picked = new Set();

    app.appendChild(el("a", { className: "back-link", href: `#/setup/${scope}`, text: "← Настройки" }));

    const bar = el("div", { className: "quiz-progress" });
    bar.appendChild(el("span", { style: `width:${(idx / questions.length) * 100}%` }));
    app.appendChild(bar);

    const card = el("div", { className: "question-card" });
    const head = el("div", { className: "question-head" }, [
      el("span", { className: "question-index", text: `Вопрос ${idx + 1} из ${questions.length}` }),
      scope === "pool" ? el("span", { className: "question-source", text: q.setTitle }) : null,
    ]);
    card.appendChild(head);
    card.appendChild(el("div", { className: "question-text", text: q.text }));
    if (multi) {
      card.appendChild(el("div", {
        className: "multi-hint",
        text: `Несколько верных ответов — выберите ${q.correct.length}`,
      }));
    }

    const list = el("div", { className: "option-list" });
    q.options.forEach((opt, i) => {
      const btn = el("button", {
        className: "option-btn",
        attrs: { type: "button", "data-i": String(i) },
      }, [
        el("span", { className: "option-key", text: String(i + 1) }),
        el("span", { className: "option-text", text: opt }),
      ]);
      btn.addEventListener("click", () => onPick(i, btn));
      list.appendChild(btn);
    });
    card.appendChild(list);
    app.appendChild(card);

    const primary = el("button", {
      className: "btn",
      attrs: { id: "primaryBtn" },
      text: multi ? "Проверить" : idx === questions.length - 1 ? "Результаты →" : "Дальше →",
      disabled: true,
      onClick: () => (multi && state.answers[idx] === null ? check() : advance()),
    });
    app.appendChild(el("div", { className: "quiz-actions" }, [primary]));

    if (answered !== null) reveal(answered);
    updateBadge();

    function onPick(i, btn) {
      if (state.answers[idx] !== null) return;
      if (multi) {
        if (picked.has(i)) picked.delete(i);
        else picked.add(i);
        btn.classList.toggle("picked", picked.has(i));
        primary.disabled = picked.size === 0;
      } else {
        commit([i]);
      }
    }

    function check() {
      commit([...picked].sort((a, b) => a - b));
    }

    function commit(chosen) {
      const isRight =
        chosen.length === q.correct.length && chosen.every((c) => q.correct.includes(c));
      state.answers[idx] = chosen;
      if (isRight) state.score++;
      Progress.mark(q.setId, q.index, isRight);
      reveal(chosen);
      updateBadge();
      primary.disabled = false;
      // отдельный обработчик здесь не нужен: основной сам выберет advance(),
      // как только у вопроса появился ответ. Иначе клик сработает дважды и
      // тест перескочит через вопрос.
      primary.textContent = idx === questions.length - 1 ? "Результаты →" : "Дальше →";
    }

    function reveal(chosen) {
      list.querySelectorAll(".option-btn").forEach((b) => {
        const i = Number(b.dataset.i);
        b.disabled = true;
        b.classList.remove("picked");
        if (q.correct.includes(i)) b.classList.add("correct");
        else if (chosen.includes(i)) b.classList.add("wrong");
      });
      primary.disabled = false;
    }

    function advance() {
      if (idx === questions.length - 1) drawResults();
      else {
        state.i++;
        drawQuestion();
      }
    }
  }

  function drawResults() {
    clear(app);
    badge.hidden = true;
    document.removeEventListener("keydown", onKey);

    const total = questions.length;
    const pct = Math.round((state.score / total) * 100);
    const wrong = questions
      .map((q, i) => ({ q, chosen: state.answers[i] || [] }))
      .filter(({ q, chosen }) =>
        !(chosen.length === q.correct.length && chosen.every((c) => q.correct.includes(c))));

    const verdict = pct >= 90 ? "Отличный результат" : pct >= 70 ? "Хороший результат" : "Есть над чем поработать";

    app.appendChild(el("div", { className: "result-card" }, [
      progressRing(pct, `${pct}%`, `${state.score} из ${total}`),
      el("h2", { text: verdict }),
      el("div", { className: "result-actions" }, [
        el("a", { className: "btn", href: `#/setup/${scope}`, text: "Ещё раз" }),
        wrong.length
          ? el("a", {
              className: "btn secondary",
              href: `#/quiz/${scope}?count=${wrong.length}&order=shuffle&filter=wrong`,
              text: "Работа над ошибками",
            })
          : null,
        el("a", { className: "btn ghost", href: "#/", text: "К списку" }),
      ]),
    ]));

    if (!wrong.length) {
      app.appendChild(el("p", { className: "all-right", text: "Все ответы верны 🎉" }));
      return;
    }

    app.appendChild(el("h3", { className: "review-title", text: `Разбор ошибок (${wrong.length})` }));
    const list = el("div", { className: "review-list" });
    for (const { q, chosen } of wrong) {
      list.appendChild(el("div", { className: "review-item" }, [
        el("div", { className: "review-q", text: q.text }),
        el("div", {
          className: "review-your",
          text: "Ваш ответ: " + (chosen.length ? chosen.map((i) => q.options[i]).join("; ") : "нет ответа"),
        }),
        el("div", {
          className: "review-correct",
          text: "Правильный: " + q.correct.map((i) => q.options[i]).join("; "),
        }),
      ]));
    }
    app.appendChild(list);
  }
}

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", render);
