#!/usr/bin/env python3
"""Отчёт о ходе ручной проверки ответов -> PROGRESS.md.

Файл переписывается после каждой партии, так что за ходом работы можно
следить прямо в репозитории.
"""
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from matching import qhash
from fixes import load as load_fixes, load_reviewed

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SKIP = {"manifest.json", "ai_answers.json", "answer_fixes.json", "reviewed.json"}
TAGS = {"verified": "✅ ключ из документа", "marked": "🖍 маркер в PDF",
        "restored": "🔑 восстановленный", "ai": "🤖 ответ модели",
        "disputed": "⚠️ спорный"}


def bar(done, total, width=28):
    filled = 0 if not total else round(width * done / total)
    return "█" * filled + "·" * (width - filled)


def main():
    reviewed = load_reviewed()
    fixes = load_fixes()
    rows, by_tag_done, by_tag_all = [], Counter(), Counter()
    total = done = 0

    for path in sorted(DATA.glob("*.json")):
        if path.name in SKIP:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        seen = reviewed.get(data["id"], {})
        n = len(data["questions"])
        d = sum(1 for q in data["questions"] if qhash(q["q"]) in seen)
        for q in data["questions"]:
            by_tag_all[q["tag"]] += 1
            if qhash(q["q"]) in seen:
                by_tag_done[q["tag"]] += 1
        rows.append((data["id"], data["title"], d, n))
        total += n
        done += d

    changed = sum(1 for v in fixes.values() for f in v.values() if not f.get("drop"))
    dropped = sum(1 for v in fixes.values() for f in v.values() if f.get("drop"))

    out = [
        "# Проверка ответов — ход работы",
        "",
        f"Обновлено: {datetime.now():%d.%m.%Y %H:%M}",
        "",
        f"## Проверено {done} из {total} — {done * 100 // max(total, 1)}%",
        "",
        "```",
        f"{bar(done, total, 40)}  {done}/{total}",
        "```",
        "",
        f"**Исправлено ответов: {changed}**  ·  снято испорченных вопросов: {dropped}",
        "",
        "## По надёжности ответа",
        "",
        "| Слой | Проверено | Всего | |",
        "|---|---:|---:|---|",
    ]
    for tag, name in TAGS.items():
        if not by_tag_all[tag]:
            continue
        out.append(f"| {name} | {by_tag_done[tag]} | {by_tag_all[tag]} | "
                   f"`{bar(by_tag_done[tag], by_tag_all[tag])}` |")

    out += ["", "## По наборам", "", "| Набор | Проверено | Всего | |", "|---|---:|---:|---|"]
    for sid, title, d, n in sorted(rows, key=lambda r: (-r[2] / max(r[3], 1), r[0])):
        out.append(f"| {title} | {d} | {n} | `{bar(d, n, 20)}` |")

    (ROOT / "PROGRESS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"проверено {done}/{total} ({done * 100 // max(total, 1)}%), исправлено {changed}")


if __name__ == "__main__":
    main()
