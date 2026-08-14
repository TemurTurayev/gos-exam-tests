// Мелкие помощники для сборки DOM. Текст всегда идёт через textContent —
// в вопросах встречаются символы вроде «<», и подстановка через innerHTML
// была бы и небезопасной, и ломала бы разметку.

function el(tag, opts = {}, children = []) {
  const node = document.createElement(tag);
  if (opts.className) node.className = opts.className;
  if (opts.text !== undefined) node.textContent = opts.text;
  if (opts.href !== undefined) node.href = opts.href;
  if (opts.title !== undefined) node.title = opts.title;
  if (opts.disabled) node.disabled = true;
  if (opts.style) node.style.cssText = opts.style;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  if (opts.onClick) node.addEventListener("click", opts.onClick);
  for (const c of children) if (c) node.appendChild(c);
  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

/** Полоска прогресса: доля верных / доля ошибок от общего числа. */
function progressBar(right, wrong, total, className = "pbar") {
  const bar = el("div", { className });
  const pctRight = total ? (right / total) * 100 : 0;
  const pctWrong = total ? (wrong / total) * 100 : 0;
  bar.appendChild(el("span", { className: "pbar-right", style: `width:${pctRight}%` }));
  bar.appendChild(el("span", { className: "pbar-wrong", style: `width:${pctWrong}%` }));
  return bar;
}

/** Кольцевой индикатор для шапки главной страницы. */
function progressRing(percent, label, sub) {
  const size = 104, stroke = 9, r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
  svg.setAttribute("class", "ring");

  const mk = (cls, dash) => {
    const c = document.createElementNS(svgNS, "circle");
    c.setAttribute("cx", size / 2);
    c.setAttribute("cy", size / 2);
    c.setAttribute("r", r);
    c.setAttribute("fill", "none");
    c.setAttribute("stroke-width", stroke);
    c.setAttribute("stroke-linecap", "round");
    c.setAttribute("class", cls);
    if (dash) c.setAttribute("stroke-dasharray", dash);
    return c;
  };
  svg.appendChild(mk("ring-track"));
  svg.appendChild(mk("ring-value", `${(circ * percent) / 100} ${circ}`));

  return el("div", { className: "ring-wrap" }, [
    svg,
    el("div", { className: "ring-label" }, [
      el("strong", { text: label }),
      el("span", { text: sub }),
    ]),
  ]);
}

/** Группа кнопок-«чипов» с одним выбранным значением. */
function chipGroup(options, initial, onChange) {
  const row = el("div", { className: "chip-row" });
  const chips = [];
  let value = initial;
  for (const opt of options) {
    const chip = el("button", {
      className: "chip" + (opt.value === initial ? " active" : ""),
      text: opt.label,
      attrs: { type: "button" },
      onClick: () => {
        value = opt.value;
        chips.forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        onChange(value, chip);
      },
    });
    chip.dataset.value = String(opt.value);
    chips.push(chip);
    row.appendChild(chip);
  }
  return { row, chips, get value() { return value; } };
}
