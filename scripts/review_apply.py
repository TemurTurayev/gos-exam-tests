#!/usr/bin/env python3
"""Запись результата ручной проверки партии вопросов.

Вход — строки на stdin, по одной на вопрос:

    <набор> <хеш> ok                       ответ верный, ничего не меняем
    <набор> <хеш> = <кусок варианта> | <почему>    ответ заменить

Кусок варианта ищется в вариантах этого вопроса, несколько правильных
разделяются знаком «+». Правки ложатся в data/answer_fixes.json, отметки
о проверке — в data/reviewed.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from matching import qhash
from fixes import load as load_fixes, save as save_fixes, load_reviewed, REVIEWED

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def question_index():
    """{(набор, хеш): вопрос} по всем опубликованным наборам."""
    index = {}
    for path in sorted(DATA.glob("*.json")):
        if path.name in ("manifest.json", "ai_answers.json",
                         "answer_fixes.json", "reviewed.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for q in data["questions"]:
            index.setdefault((data["id"], qhash(q["q"])), q)
    return index


def main():
    index = question_index()
    fixes = load_fixes()
    reviewed = load_reviewed()
    ok = changed = 0
    problems = []

    # --batch N: подтвердить первые N вопросов очереди, кроме перечисленных.
    # Так на партию в двести вопросов уходит несколько строк вместо двухсот.
    window = None
    if "--batch" in sys.argv:
        from review_dump import pending
        size = int(sys.argv[sys.argv.index("--batch") + 1])
        window = [(sid, h) for sid, h, _ in pending()[:size]]

    for line in sys.stdin:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            problems.append(f"непонятная строка: {line}")
            continue
        sid, h, rest = parts
        q = index.get((sid, h))
        if q is None:
            problems.append(f"{sid} {h}: вопрос не найден")
            continue

        if rest.strip() == "ok":
            reviewed.setdefault(sid, {})[h] = "проверено, ответ верный"
            ok += 1
            continue

        if rest.startswith("drop"):
            why = rest[4:].strip(" |") or "вопрос испорчен в исходнике"
            fixes.setdefault(sid, {})[h] = {"drop": True, "why": why}
            reviewed.setdefault(sid, {})[h] = "снят: " + why
            changed += 1
            continue

        if not rest.startswith("="):
            problems.append(f"{sid} {h}: ожидалось «ok» или «= вариант | причина»")
            continue

        body = rest[1:]
        answer, _, why = body.partition("|")
        texts = []
        for frag in answer.split("+"):
            frag = frag.strip()
            if not frag:
                continue
            # точное совпадение важнее вхождения: «5 mln» есть и внутри «3,5 mln»
            exact = [o for o in q["options"] if o.strip().lower() == frag.lower()]
            hits = exact or [o for o in q["options"] if frag.lower() in o.lower()]
            if len(hits) != 1:
                problems.append(f"{sid} {h}: «{frag}» найден {len(hits)} раз")
                break
            texts.append(hits[0])
        else:
            fixes.setdefault(sid, {})[h] = {
                "correct": texts, "why": why.strip() or "ручная проверка"}
            reviewed.setdefault(sid, {})[h] = "проверено, ответ исправлен"
            changed += 1

    if problems:
        print("НЕ ПРИМЕНЕНО:")
        for p in problems:
            print("  " + p)
        return 1

    if window is not None:
        for sid, h in window:
            bucket = reviewed.setdefault(sid, {})
            if h not in bucket:
                bucket[h] = "проверено, ответ верный"
                ok += 1

    save_fixes(fixes)
    REVIEWED.write_text(json.dumps(reviewed, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in reviewed.values())
    print(f"подтверждено: {ok}, исправлено: {changed}, проверено всего: {total}")

    import progress            # PROGRESS.md — чтобы за ходом работы было видно
    progress.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
