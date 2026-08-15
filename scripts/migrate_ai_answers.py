#!/usr/bin/env python3
"""Перенос ответов модели на вопросы после починки разбора PDF.

Ответы хранятся по хешу текста вопроса. Когда разбор исправляется (например,
к вопросу возвращается перенесённый хвост), хеш меняется и ответ теряется.
Сопоставляем старые и новые вопросы по набору вариантов — он остаётся тем же —
и переносим ответ по ТЕКСТУ правильного варианта, а не по его номеру: порядок
и состав вариантов тоже могли измениться.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_extra import qhash, pending_questions
from matching import key

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = Path(__file__).resolve().parent / "_ai_snapshot.json"
AI_FILE = ROOT / "data" / "ai_answers.json"


def option_signature(options):
    """Ключ вопроса по вариантам: устойчив к правкам текста вопроса."""
    return tuple(sorted(key(o) for o in options if o.strip()))


def main():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    # существующие ответы сохраняем: у большинства вопросов текст не изменился,
    # и их хеши по-прежнему действительны
    result = json.loads(AI_FILE.read_text(encoding="utf-8")) if AI_FILE.exists() else {}
    pending = pending_questions()          # вопросы, оставшиеся без ответа
    stats = {}

    for sid, old_items in snapshot.items():
        # старые вопросы, разложенные по набору вариантов
        by_options = {}
        for item in old_items:
            by_options.setdefault(option_signature(item["options"]), item)

        moved = lost = 0
        answers = result.setdefault(sid, {})
        for h, q in pending.get(sid, []):
            old = by_options.get(option_signature(q["options"]))
            if not old:
                lost += 1
                continue
            wanted = {key(t) for t in old["correct_text"]}
            idx = [i for i, o in enumerate(q["options"]) if key(o) in wanted]
            if len(idx) == 1:
                answers[h] = idx[0]
                moved += 1
            else:
                lost += 1
        stats[sid] = (len(old_items), moved, lost)

    AI_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'набор':24s} {'в снимке':>8s} {'перенесено':>11s} {'не сошлось':>11s}")
    for sid, (was, moved, lost) in stats.items():
        print(f"{sid:24s} {was:8d} {moved:11d} {lost:11d}")
    print("\nвсего ответов после переноса:", sum(len(v) for v in result.values()))


if __name__ == "__main__":
    main()
