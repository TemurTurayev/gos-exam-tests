// Экраны приложения: вход по имени -> главная -> настройка -> тест -> итоги.

const app = document.getElementById("app");
const badge = document.getElementById("scoreBadge");
const userChip = document.getElementById("userChip");
const langSwitch = document.getElementById("langSwitch");

const TEST_LANG_KEY = "gos-exam-testlang";

const TestLang = {
  get() {
    try { return localStorage.getItem(TEST_LANG_KEY) || I18N.lang; } catch { return "ru"; }
  },
  set(v) {
    try { localStorage.setItem(TEST_LANG_KEY, v); } catch { /* приватный режим */ }
  },
};

const t = (...a) => I18N.t(...a);

/** Название набора и предмета на языке интерфейса. */
const setTitle = (s) => (I18N.lang === "uz" && s.title_uz) || s.title;
const setSubject = (s) => (I18N.lang === "uz" && s.subject_uz) || s.subject;

// ------------------------------------------------------------------ шапка --
function renderChrome() {
  document.documentElement.lang = I18N.lang;
  document.getElementById("brandText").textContent = t("appName");
  document.getElementById("footerText").textContent = t("footer");

  clear(langSwitch);
  for (const code of ["ru", "uz"]) {
    langSwitch.appendChild(el("button", {
      className: "lang-btn" + (I18N.lang === code ? " active" : ""),
      text: code === "ru" ? "RU" : "UZ",
      attrs: { type: "button", title: code === "ru" ? "Русский" : "O‘zbekcha" },
      onClick: () => { I18N.set(code); render(); },
    }));
  }

  if (User.name) {
    userChip.hidden = false;
    userChip.textContent = User.name;
    userChip.title = t("changeUser");
    userChip.onclick = () => {
      User.clear();
      Progress.invalidate();
      location.hash = "#/";
      render();
    };
  } else {
    userChip.hidden = true;
  }
}

// ---------------------------------------------------------------- роутинг --
function parseHash() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, query] = raw.split("?");
  return { parts: path.split("/").filter(Boolean), params: new URLSearchParams(query || "") };
}

async function render() {
  badge.hidden = true;
  renderChrome();
  clear(app);

  if (!User.name) return renderWelcome();

  const { parts, params } = parseHash();
  try {
    if (!parts.length) await renderHome();
    else if (parts[0] === "setup" && parts[1]) await renderSetup(parts[1]);
    else if (parts[0] === "quiz" && parts[1]) await renderQuiz(parts[1], params);
    else notFound();
  } catch (err) {
    console.error(err);
    clear(app);
    app.appendChild(el("div", { className: "empty-state", text: String(err.message || err) }));
  }
}

function notFound() {
  app.appendChild(el("div", { className: "empty-state" }, [
    el("p", { text: "404" }),
    el("a", { className: "btn", href: "#/", text: t("toList") }),
  ]));
}

function loading(msg) {
  clear(app);
  app.appendChild(el("div", { className: "empty-state", text: msg || t("loading") }));
}

// -------------------------------------------------------------------- вход --
function renderWelcome() {
  const card = el("div", { className: "welcome-card" });
  card.appendChild(el("div", { className: "welcome-mark", text: "🩺" }));
  card.appendChild(el("h1", { text: t("welcomeTitle") }));
  card.appendChild(el("p", { className: "welcome-sub", text: t("welcomeSub") }));

  const label = el("label", { className: "welcome-label", text: t("nameLabel") });
  const input = el("input", {
    className: "text-input",
    attrs: {
      type: "text", id: "nameInput", maxlength: "30",
      placeholder: t("namePlaceholder"), autocomplete: "off", spellcheck: "false",
    },
  });
  const error = el("p", { className: "input-error" });
  const submit = el("button", { className: "btn big", text: t("nameStart") });

  const tryStart = () => {
    const res = User.validate(input.value);
    if (!res.ok) {
      error.textContent = t(res.error);
      input.classList.add("invalid");
      input.focus();
      return;
    }
    User.set(res.value);
    Progress.invalidate();
    Leaderboard.remember(res.value, User.slug);
    location.hash = "#/";
    render();
  };

  submit.addEventListener("click", tryStart);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") tryStart(); });
  input.addEventListener("input", () => {
    error.textContent = "";
    input.classList.remove("invalid");
  });

  card.appendChild(label);
  card.appendChild(input);
  card.appendChild(error);
  card.appendChild(submit);
  app.appendChild(card);
  setTimeout(() => input.focus(), 50);
}

// ----------------------------------------------------------------- главная --
async function renderHome() {
  loading();
  const manifest = await Data.loadManifest();
  clear(app);

  const lang = TestLang.get();
  const visible = manifest.filter((s) => lang === "all" || s.language === lang);
  const totals = Progress.totals(visible);
  const pct = totals.total ? Math.round((totals.done / totals.total) * 100) : 0;
  const accuracy = totals.done ? Math.round((totals.right / totals.done) * 100) : 0;

  app.appendChild(el("section", { className: "hero" }, [
    progressRing(pct, `${pct}%`, t("passed")),
    el("div", { className: "hero-text" }, [
      el("h1", { text: `${t("hello")}, ${User.name}!` }),
      el("p", {
        className: "hero-sub",
        text: `${visible.length} ${t("sets")} · ${totals.total.toLocaleString("ru-RU")} ${t("questions")}`,
      }),
      el("div", { className: "hero-stats" }, [
        statChip(t("statDone"), totals.done.toLocaleString("ru-RU")),
        statChip(t("statRight"), totals.done ? `${accuracy}%` : "—"),
        statChip(t("statLeft"), (totals.total - totals.done).toLocaleString("ru-RU")),
      ]),
    ]),
  ]));

  // язык тестов
  const langField = el("div", { className: "lang-field" });
  langField.appendChild(el("span", { className: "lang-field-label", text: t("langOfTests") }));
  const langTabs = chipGroup(
    [
      { value: "all", label: t("langAll") },
      { value: "ru", label: t("langRu") },
      { value: "uz", label: t("langUz") },
    ],
    lang,
    (value) => { TestLang.set(value); renderHome(); }
  );
  langField.appendChild(langTabs.row);
  app.appendChild(langField);

  app.appendChild(el("a", { className: "pool-card", href: "#/setup/pool" }, [
    el("div", { className: "pool-icon", text: "🎲" }),
    el("div", { className: "pool-body" }, [
      el("div", { className: "pool-title", text: t("poolTitle") }),
      el("div", { className: "pool-sub", text: t("poolSub") }),
    ]),
    el("div", { className: "pool-go", text: "→" }),
  ]));

  app.appendChild(tagLegend(visible));

  if (totals.done) {
    app.appendChild(el("div", { className: "row-actions" }, [
      el("button", {
        className: "btn ghost small",
        text: t("resetAll"),
        onClick: () => {
          if (confirm(t("resetAllConfirm"))) { Progress.reset(); renderHome(); }
        },
      }),
    ]));
  }

  const bySubject = new Map();
  for (const set of visible) {
    const subject = setSubject(set);
    if (!bySubject.has(subject)) bySubject.set(subject, []);
    bySubject.get(subject).push(set);
  }
  for (const [subject, sets] of bySubject) {
    const section = el("section", { className: "subject-group" });
    section.appendChild(el("h2", { className: "subject-title", text: subject }));
    const list = el("div", { className: "set-list" });
    for (const set of sets) list.appendChild(setCard(set));
    section.appendChild(list);
    app.appendChild(section);
  }

  // таблица лидеров — внизу страницы
  const board = el("section", { className: "board" });
  app.appendChild(board);
  renderLeaderboard(board);
}

/** Таблица лидеров: общая, если настроено хранилище, иначе по этому устройству. */
async function renderLeaderboard(box) {
  // сначала отправляем свой результат и дожидаемся ответа, иначе таблица
  // успеет загрузиться раньше и новый участник не увидит себя в списке
  await Leaderboard.publish();
  const { scope, rows } = await Leaderboard.rows();
  clear(box);

  box.appendChild(el("div", { className: "board-head" }, [
    el("h2", { className: "board-title", text: `🏆 ${t("boardTitle")}` }),
    el("span", { className: "board-scope", text: scope === "global" ? t("boardGlobal") : t("boardLocal") }),
  ]));

  if (!rows.length) {
    box.appendChild(el("p", { className: "board-empty", text: t("boardEmpty") }));
    return;
  }

  const table = el("table", { className: "board-table" });
  const head = el("tr", {}, [
    el("th", { className: "col-place", text: "#" }),
    el("th", { text: t("boardName") }),
    el("th", { className: "num col-solved", text: t("boardSolved") }),
    el("th", { className: "num", text: t("boardCorrect") }),
    el("th", { className: "num", text: t("boardAccuracy") }),
  ]);
  table.appendChild(el("thead", {}, [head]));

  const medals = ["🥇", "🥈", "🥉"];
  const body = el("tbody");
  rows.slice(0, 20).forEach((r, i) => {
    const isMe = r.name === User.name;
    const name = el("td", {}, [
      el("span", { text: r.name }),
      isMe ? el("span", { className: "board-you", text: t("boardYou") }) : null,
    ]);
    body.appendChild(el("tr", { className: isMe ? "me" : "" }, [
      el("td", { className: "col-place", text: medals[i] || String(i + 1) }),
      name,
      el("td", { className: "num col-solved", text: r.solved.toLocaleString("ru-RU") }),
      el("td", { className: "num strong", text: r.correct.toLocaleString("ru-RU") }),
      el("td", { className: "num dim", text: `${Math.round(r.accuracy * 100)}%` }),
    ]));
  });
  table.appendChild(body);
  box.appendChild(el("div", { className: "board-scroll" }, [table]));
}

function statChip(label, value) {
  return el("div", { className: "stat-chip" }, [
    el("span", { className: "stat-value", text: value }),
    el("span", { className: "stat-label", text: label }),
  ]);
}

/** Легенда тегов с количеством вопросов каждого вида. */
function tagLegend(sets) {
  const totals = {};
  for (const s of sets) {
    for (const [tag, n] of Object.entries(s.tags || {})) {
      totals[tag] = (totals[tag] || 0) + n;
    }
  }
  const box = el("details", { className: "legend" });
  box.appendChild(el("summary", { text: t("tagsTitle") }));
  const list = el("div", { className: "legend-list" });
  for (const [tag, meta] of Object.entries(TAG_META)) {
    if (!totals[tag]) continue;
    list.appendChild(el("div", { className: "legend-item" }, [
      el("span", { className: `tag ${meta.cls}`, text: `${meta.icon} ${t(meta.label)}` }),
      el("span", { className: "legend-count", text: totals[tag].toLocaleString("ru-RU") }),
      el("span", { className: "legend-hint", text: t(meta.hint) }),
    ]));
  }
  box.appendChild(list);
  return box;
}

function setCard(set) {
  const s = Progress.stats(set.id, set.count);
  const card = el("a", { className: "set-card", href: `#/setup/${set.id}` });

  card.appendChild(el("div", { className: "set-head" }, [
    el("div", { className: "set-title", text: setTitle(set) }),
    el("span", { className: `pill lang-${set.language}`, text: set.language.toUpperCase() }),
  ]));

  const tags = el("div", { className: "set-tags" });
  for (const [tag, meta] of Object.entries(TAG_META)) {
    const n = (set.tags || {})[tag];
    if (!n) continue;
    tags.appendChild(el("span", {
      className: `tag tiny ${meta.cls}`,
      text: `${meta.icon} ${n}`,
      title: t(meta.hint),
    }));
  }
  card.appendChild(tags);

  card.appendChild(el("div", { className: "set-meta" }, [
    el("span", { text: `${set.count} ${t("questions")}` }),
    el("span", {
      className: s.done ? "set-done" : "set-done muted",
      text: s.done
        ? `${t("solved")} ${s.done} · ${t("correctShare")} ${Math.round((s.right / s.done) * 100)}%`
        : t("notStarted"),
    }),
  ]));
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

  const testLang = TestLang.get();
  const pooled = manifest.filter((m) => testLang === "all" || m.language === testLang);
  const total = isPool ? pooled.reduce((s, m) => s + m.count, 0) : meta.count;
  const stats = isPool ? Progress.totals(pooled) : Progress.stats(scope, total);

  clear(app);
  app.appendChild(el("a", { className: "back-link", href: "#/", text: t("backToList") }));

  const card = el("div", { className: "setup-card" });
  card.appendChild(el("h2", { text: isPool ? t("poolTitle") : setTitle(meta) }));
  card.appendChild(el("p", {
    className: "setup-sub",
    text: `${total.toLocaleString("ru-RU")} ${t("questions")} · ${t("solved")} ${stats.done.toLocaleString("ru-RU")}`,
  }));

  let filter = "all", trust = "all", count = 20, order = "shuffle";
  const note = el("p", { className: "available-note" });

  const filterGroup = chipGroup(
    [
      { value: "all", label: t("filterAll") },
      { value: "unsolved", label: t("filterUnsolved") },
      { value: "wrong", label: t("filterWrong") },
    ],
    "all",
    (v) => { filter = v; refresh(); }
  );
  card.appendChild(field(t("whichQuestions"), filterGroup.row));

  const trustGroup = chipGroup(
    [
      { value: "all", label: t("trustAll") },
      { value: "strict", label: `✅ ${t("trustStrict")}` },
      { value: "flagged", label: `⚠️ ${t("trustFlagged")}` },
    ],
    "all",
    (v) => { trust = v; refresh(); }
  );
  card.appendChild(field(t("trust"), trustGroup.row));
  card.appendChild(note);

  const countGroup = chipGroup(
    [10, 20, 30, 50, 100].map((n) => ({ value: n, label: String(n) }))
      .concat([{ value: 0, label: t("all") }]),
    20,
    (v) => { count = v; }
  );
  card.appendChild(field(t("howMany"), countGroup.row));

  const orderGroup = chipGroup(
    [{ value: "shuffle", label: t("shuffle") }, { value: "sequential", label: t("sequential") }],
    "shuffle",
    (v) => { order = v; }
  );
  card.appendChild(field(t("order"), orderGroup.row));

  const startBtn = el("button", {
    className: "btn big",
    text: t("start"),
    onClick: () => {
      const n = count === 0 ? 99999 : count;
      location.hash = `#/quiz/${scope}?count=${n}&order=${order}&filter=${filter}&trust=${trust}`;
    },
  });
  card.appendChild(startBtn);

  if (stats.done) {
    card.appendChild(el("button", {
      className: "btn ghost small",
      text: isPool ? t("resetAll") : t("resetSet"),
      onClick: () => {
        if (confirm(isPool ? t("resetAllConfirm") : t("resetSetConfirm"))) {
          Progress.reset(isPool ? undefined : scope);
          renderSetup(scope);
        }
      },
    }));
  }
  app.appendChild(card);

  async function refresh() {
    const n = await Data.countAvailable({ scope, filter, trust, testLang });
    note.textContent = n === 0
      ? t("nothingLeft")
      : (filter === "all" && trust === "all" ? "" : `${t("available")}: ${n.toLocaleString("ru-RU")}`);
    startBtn.disabled = n === 0;
  }
  refresh();
}

function field(labelText, control) {
  return el("div", { className: "field" }, [el("label", { text: labelText }), control]);
}

// -------------------------------------------------------------------- тест --
async function renderQuiz(scope, params) {
  loading(t("preparing"));
  const questions = await Data.buildQuiz({
    scope,
    count: Number(params.get("count")) || 20,
    order: params.get("order") || "shuffle",
    filter: params.get("filter") || "all",
    trust: params.get("trust") || "all",
    testLang: TestLang.get(),
  });
  clear(app);

  if (!questions.length) {
    app.appendChild(el("div", { className: "empty-state" }, [
      el("p", { text: t("noQuestions") }),
      el("a", { className: "btn", href: `#/setup/${scope}`, text: t("changeSettings") }),
    ]));
    return;
  }

  const state = { i: 0, answers: new Array(questions.length).fill(null), score: 0 };

  const onKey = (e) => {
    if (e.key >= "1" && e.key <= "9") {
      const btn = app.querySelector(`.option-btn[data-i="${Number(e.key) - 1}"]`);
      if (btn && !btn.disabled) btn.click();
    } else if (e.key === "Enter") {
      const next = document.getElementById("primaryBtn");
      if (next && !next.disabled) next.click();
    }
  };
  document.addEventListener("keydown", onKey);
  window.addEventListener("hashchange",
    () => document.removeEventListener("keydown", onKey), { once: true });

  drawQuestion();

  function updateBadge() {
    const answered = state.answers.filter((a) => a !== null).length;
    badge.hidden = answered === 0;
    if (!answered) return;
    badge.textContent = `${state.score} / ${answered}`;
    badge.className = "score-badge" + (state.score / answered < 0.6 ? " low" : "");
  }

  function drawQuestion() {
    clear(app);
    const idx = state.i;
    const q = questions[idx];
    const multi = q.correct.length > 1;
    const picked = new Set();

    app.appendChild(el("a", { className: "back-link", href: `#/setup/${scope}`, text: t("backToSetup") }));

    const bar = el("div", { className: "quiz-progress" });
    bar.appendChild(el("span", { style: `width:${(idx / questions.length) * 100}%` }));
    app.appendChild(bar);

    const card = el("div", { className: "question-card" });
    const tagMeta = TAG_META[q.tag] || TAG_META.verified;
    card.appendChild(el("div", { className: "question-head" }, [
      el("span", { className: "question-index", text: t("questionOf", idx + 1, questions.length) }),
      el("span", {
        className: `tag ${tagMeta.cls}`,
        text: `${tagMeta.icon} ${t(tagMeta.label)}`,
        title: t(tagMeta.hint),
      }),
    ]));
    if (scope === "pool") {
      card.appendChild(el("div", { className: "question-source", text: q.setTitle }));
    }
    card.appendChild(el("div", { className: "question-text", text: q.text }));
    if (multi) {
      card.appendChild(el("div", { className: "multi-hint", text: t("multiHint", q.correct.length) }));
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
      text: multi ? t("check") : (idx === questions.length - 1 ? t("toResults") : t("next")),
      disabled: true,
      onClick: () => (state.answers[idx] === null ? commit([...picked].sort((a, b) => a - b)) : advance()),
    });
    app.appendChild(el("div", { className: "quiz-actions" }, [primary]));
    updateBadge();

    function onPick(i, btn) {
      if (state.answers[idx] !== null) return;
      if (!multi) return commit([i]);
      if (picked.has(i)) picked.delete(i);
      else picked.add(i);
      btn.classList.toggle("picked", picked.has(i));
      primary.disabled = picked.size === 0;
    }

    function commit(chosen) {
      if (!chosen.length) return;
      const right = chosen.length === q.correct.length && chosen.every((c) => q.correct.includes(c));
      state.answers[idx] = chosen;
      if (right) state.score++;
      Progress.mark(q.setId, q.index, right);

      list.querySelectorAll(".option-btn").forEach((b) => {
        const i = Number(b.dataset.i);
        b.disabled = true;
        b.classList.remove("picked");
        if (q.correct.includes(i)) b.classList.add("correct");
        else if (chosen.includes(i)) b.classList.add("wrong");
      });

      updateBadge();
      primary.disabled = false;
      primary.textContent = idx === questions.length - 1 ? t("toResults") : t("next");
    }

    function advance() {
      if (idx === questions.length - 1) drawResults();
      else { state.i++; drawQuestion(); }
    }
  }

  function drawResults() {
    clear(app);
    badge.hidden = true;
    document.removeEventListener("keydown", onKey);
    Leaderboard.publish();          // в локальном режиме ничего не делает

    const total = questions.length;
    const pct = Math.round((state.score / total) * 100);
    const wrong = questions
      .map((q, i) => ({ q, chosen: state.answers[i] || [] }))
      .filter(({ q, chosen }) =>
        !(chosen.length === q.correct.length && chosen.every((c) => q.correct.includes(c))));

    app.appendChild(el("div", { className: "result-card" }, [
      progressRing(pct, `${pct}%`, `${state.score} / ${total}`),
      el("h2", { text: pct >= 90 ? t("resultGreat") : pct >= 70 ? t("resultGood") : t("resultPoor") }),
      el("div", { className: "result-actions" }, [
        el("a", { className: "btn", href: `#/setup/${scope}`, text: t("again") }),
        wrong.length
          ? el("a", {
              className: "btn secondary",
              href: `#/quiz/${scope}?count=${wrong.length}&order=shuffle&filter=wrong&trust=all`,
              text: t("workOnMistakes"),
            })
          : null,
        el("a", { className: "btn ghost", href: "#/", text: t("toList") }),
      ]),
    ]));

    if (!wrong.length) {
      app.appendChild(el("p", { className: "all-right", text: t("allRight") }));
      return;
    }

    app.appendChild(el("h3", { className: "review-title", text: t("mistakes", wrong.length) }));
    const list = el("div", { className: "review-list" });
    for (const { q, chosen } of wrong) {
      const meta = TAG_META[q.tag] || TAG_META.verified;
      list.appendChild(el("div", { className: "review-item" }, [
        el("div", { className: "review-q", text: q.text }),
        el("div", {
          className: "review-your",
          text: `${t("yourAnswer")}: ` +
            (chosen.length ? chosen.map((i) => q.options[i]).join("; ") : t("noAnswer")),
        }),
        el("div", {
          className: "review-correct",
          text: `${t("correctAnswer")}: ` + q.correct.map((i) => q.options[i]).join("; "),
        }),
        el("span", { className: `tag tiny ${meta.cls}`, text: `${meta.icon} ${t(meta.label)}` }),
      ]));
    }
    app.appendChild(list);
  }
}

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", render);
