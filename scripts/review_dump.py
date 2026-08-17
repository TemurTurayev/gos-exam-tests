#!/usr/bin/env python3
"""Выгрузка вопросов на ручную проверку ответа.

Показывает вопросы, у которых ответ не подтверждён исходником (теги ai
и disputed) и которые ещё не проверены вручную — то есть по которым нет
записи в data/answer_fixes.json.

    python3 scripts/review_dump.py [сколько] [--set <id>]

Формат вывода рассчитан на чтение целиком: набор, хеш вопроса, текст
и пронумерованные варианты; звёздочкой помечен текущий ответ.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from matching import qhash
from fixes import load as load_fixes, load_reviewed

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CHECK_TAGS = {"ai", "disputed"}


def pending(only_set=None):
    fixes = load_fixes()
    reviewed = load_reviewed()
    out = []
    for path in sorted(DATA.glob("*.json")):
        if path.name in ("manifest.json", "ai_answers.json",
                         "answer_fixes.json", "reviewed.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if only_set and data["id"] != only_set:
            continue
        done = {**fixes.get(data["id"], {}), **reviewed.get(data["id"], {})}
        for q in data["questions"]:
            if q["tag"] not in CHECK_TAGS:
                continue
            h = qhash(q["q"])
            if h in done:
                continue
            out.append((data["id"], h, q))
    return out


def main():
    args = [a for a in sys.argv[1:]]
    only = None
    if "--set" in args:
        only = args[args.index("--set") + 1]
        args = args[:args.index("--set")]
    limit = int(args[0]) if args else 40

    items = pending(only)
    print(f"# осталось проверить: {len(items)}\n")
    for sid, h, q in items[:limit]:
        print(f"{sid} {h}")
        print(f"В: {q['q']}")
        for i, opt in enumerate(q["options"]):
            print(f"  {'*' if i in q['correct'] else ' '}{i} {opt}")
        print()


if __name__ == "__main__":
    main()
