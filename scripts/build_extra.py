#!/usr/bin/env python3
"""Сборка наборов из файлов, где ключ не размечен обычным способом.

Источник ключа отражается тегом вопроса:
  marked    — ответ подсвечен маркером в PDF;
  restored  — ключа нет, применено правило «верен первый вариант»
              (проверено сверкой с базой, см. sources/without_answers/README.md);
  ai        — ключа нет и правило не работает, ответ выбран моделью;
  disputed  — разметка исходника противоречива.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import DATA, ROOT
from matching import key, qhash
import sources_unanswered as SU
from highlights import parse_with_highlights, finalize as finalize_marks, NO_ANS

AI_FILE = ROOT / "data" / "ai_answers.json"

# файлы, где доказано правило «верен первый вариант»
POSITION_RULE = {"child-surg-hosp-ru2", "ped-ru-sources", "therapy-ru-bank"}
# файлы, где ключ снят с выделений маркером
HIGHLIGHTED = {
    "ped-uz-lat": "Pediatriya javob 98%aniq 99.pdf",
    "child-surg-uz-lat": "102-bol-hirurgia-test-sajt-uzb-495 (1).pdf",
}


def load_ai_answers():
    if not AI_FILE.exists():
        return {}
    return json.loads(AI_FILE.read_text(encoding="utf-8"))


def tagged(q, tag):
    return {"q": q["q"], "options": q["options"], "correct": q["correct"], "tag": tag}


def build():
    ai = load_ai_answers()
    banks = SU.load_all()
    out = {}

    for spec in SU.SOURCES:
        sid = spec["id"]
        questions = []

        if sid in HIGHLIGHTED:
            ready, disputed, empty = finalize_marks(
                parse_with_highlights(NO_ANS / HIGHLIGHTED[sid]))
            questions += [tagged(q, "marked") for q in ready]
            questions += [tagged(q, "disputed") for q in disputed]
            pending = empty
        elif sid in POSITION_RULE:
            questions += [tagged({**q, "correct": [0]}, "restored") for q in banks[sid]]
            pending = []
        else:
            pending = banks[sid]

        # вопросы без ключа — берём ответ из файла с ответами модели
        answers = ai.get(sid, {})
        for q in pending:
            idx = answers.get(qhash(q["q"]))
            if idx is not None and 0 <= idx < len(q["options"]):
                questions.append(tagged({**q, "correct": [idx]}, "ai"))

        if questions:
            out[sid] = {"id": sid, "title": spec["title"], "subject": spec["subject"],
                        "language": spec["language"], "questions": questions}
    return out


def pending_questions():
    """Вопросы, которые ждут ответа модели: {set_id: [(hash, q, options)]}."""
    ai = load_ai_answers()
    banks = SU.load_all()
    todo = {}
    for spec in SU.SOURCES:
        sid = spec["id"]
        if sid in POSITION_RULE:
            continue
        if sid in HIGHLIGHTED:
            _, _, empty = finalize_marks(parse_with_highlights(NO_ANS / HIGHLIGHTED[sid]))
            items = empty
        else:
            items = banks[sid]
        answered = ai.get(sid, {})
        rest = [(qhash(q["q"]), q) for q in items if qhash(q["q"]) not in answered]
        if rest:
            todo[sid] = rest
    return todo


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--pending":
        for sid, items in pending_questions().items():
            print(f"{sid}: {len(items)} без ответа")
        sys.exit()

    sets = build()
    for sid, data in sets.items():
        tags = {}
        for q in data["questions"]:
            tags[q["tag"]] = tags.get(q["tag"], 0) + 1
        print(f"{sid:22s} {len(data['questions']):5d}  {tags}")
    print("\nВсего:", sum(len(d["questions"]) for d in sets.values()))
