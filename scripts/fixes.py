#!/usr/bin/env python3
"""Ручные исправления ответов: data/answer_fixes.json.

Зачем отдельный файл. Наборы собираются заново из исходников каждой сборкой,
поэтому правку нельзя вносить прямо в data/*.json — её сотрёт следующий запуск
build_site.py. Исправления живут отдельно и применяются поверх разбора.

Формат:

    {
      "<id набора>": {
        "<хеш вопроса>": {
          "correct": ["точный текст правильного варианта", ...],
          "why": "откуда известен правильный ответ",
          "tag": "verified"          // необязательно: сменить тег
        }
      }
    }

Правильный ответ хранится ТЕКСТОМ, а не номером: при переразборе исходника
порядок и состав вариантов могут измениться, а текст — нет. Если текст найти
не удалось, сборка громко ругается, а не тихо оставляет старый ответ.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from matching import qhash

ROOT = Path(__file__).resolve().parent.parent
FIXES = ROOT / "data" / "answer_fixes.json"
REVIEWED = ROOT / "data" / "reviewed.json"


def load_reviewed():
    """Хеши вопросов, у которых ответ проверен вручную и оказался верным."""
    if not REVIEWED.exists():
        return {}
    return json.loads(REVIEWED.read_text(encoding="utf-8"))


def mark_reviewed(sid, hashes, note):
    data = load_reviewed()
    bucket = data.setdefault(sid, {})
    for h in hashes:
        bucket[h] = note
    REVIEWED.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return sum(len(v) for v in data.values())


def norm(text):
    """Сравнение вариантов без оглядки на пробелы, регистр и знаки."""
    text = unicodedata.normalize("NFKD", str(text).lower())
    return re.sub(r"[^\w]+", "", text, flags=re.U)


def load():
    if not FIXES.exists():
        return {}
    return json.loads(FIXES.read_text(encoding="utf-8"))


def save(data):
    FIXES.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def apply_all(sets):
    """Применяет исправления к собранным наборам. Возвращает отчёт."""
    fixes = load()
    applied = missed = same = 0
    problems = []

    dropped = 0
    for sid, data in sets.items():
        by_hash = fixes.get(sid, {})
        if not by_hash:
            continue
        # вопросы, которые нельзя починить: текст потерян или правильного
        # варианта в списке не осталось — их лучше не показывать вовсе
        keep = []
        for q in data["questions"]:
            if by_hash.get(qhash(q["q"]), {}).get("drop"):
                dropped += 1
                continue
            keep.append(q)
        data["questions"] = keep

        seen = set()
        for q in data["questions"]:
            fix = by_hash.get(qhash(q["q"]))
            if not fix or fix.get("drop"):
                continue
            seen.add(qhash(q["q"]))
            wanted = {norm(t) for t in fix["correct"]}
            idx = sorted(i for i, o in enumerate(q["options"]) if norm(o) in wanted)
            if len(idx) != len(wanted):
                problems.append(f"{sid} {qhash(q['q'])}: вариант не найден — {fix['correct']}")
                continue
            if idx == q["correct"] and fix.get("tag", q["tag"]) == q["tag"]:
                same += 1
            else:
                applied += 1
            q["correct"] = idx
            if fix.get("tag"):
                q["tag"] = fix["tag"]
        missed += len([h for h in by_hash
                       if h not in seen and not by_hash[h].get("drop")])

    return {"исправлено": applied, "уже совпадало": same, "снято": dropped,
            "вопрос не найден": missed, "проблемы": problems}


if __name__ == "__main__":
    data = load()
    total = sum(len(v) for v in data.values())
    print(f"исправлений в файле: {total}")
    for sid, items in sorted(data.items()):
        print(f"  {sid:24s} {len(items)}")
