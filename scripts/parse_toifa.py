#!/usr/bin/env python3
"""Разбор «тоифа 669.txt» — русский банк по терапии для аттестации на категорию.

Формат простой и для всего файла одинаковый:

    ? 12; Текст вопроса:
    + ; правильный вариант
    - ; неправильный вариант

Ключ размечен знаком «+» прямо в строке, поэтому ответ берётся из файла.
Правильный вариант всюду идёт первым — это особенность выгрузки, а не
предположение разбора: на порядок мы не опираемся, только на знак.

В файле три места, где разметка сбита, и разбор их чинит:

  * у заданий 158-160 потерян ведущий «?» — строка начинается сразу с номера;
  * задания 410 и 411 слиты в одну строку, варианты после неё принадлежат
    второму, а первое остаётся без вариантов и не попадает на сайт;
  * в задании 536 у одного варианта нет «;», а к другому приклеен хвост
    вопроса через «:;».
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import ROOT

SOURCE = ROOT / "sources" / "with_answers" / "toifa 669.txt"

SET_ID = "therapy-toifa-ru"
TITLE = "Терапия — тоифа"
TITLE_UZ = "Terapiya — toifa"
SUBJECT = "Терапия"

# «?» в выгрузке местами потерян, поэтому он необязателен
QUESTION = re.compile(r"^\??\s*(\d+)\s*;\s*(.*)$")
# «;» после знака тоже местами потерян
OPTION = re.compile(r"^([+-])\s*;?\s*(.*)$")
# два задания, слитые в одну строку: «… 411; Текст второго»
GLUED = re.compile(r"\s\d{1,4};\s")
# хвост вопроса, приклеенный к варианту через «:;»
TAIL = re.compile(r"^.*?:;\s*")


def clean_option(text):
    return TAIL.sub("", text).strip().rstrip(";").strip()


def drop_repeats(options, correct):
    """Убирает повторяющиеся варианты, сохраняя ответ.

    В двенадцати заданиях один и тот же вариант выписан дважды — иногда это
    как раз правильный ответ, и тогда на экране было бы два одинаковых
    варианта, из которых верным считается только один. Оставляем первый.
    """
    seen, kept, moved = {}, [], []
    for i, option in enumerate(options):
        low = option.lower()
        if low in seen:
            if i in correct and seen[low] not in moved:
                moved.append(seen[low])
            continue
        seen[low] = len(kept)
        if i in correct:
            moved.append(len(kept))
        kept.append(option)
    return kept, sorted(set(moved))


def read(path=SOURCE):
    questions, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue

        option = OPTION.match(line)
        if option and cur is not None:
            cur["options"].append(clean_option(option.group(2)))
            if option.group(1) == "+":
                cur["correct"].append(len(cur["options"]) - 1)
            continue

        head = QUESTION.match(line)
        if head:
            if cur:
                questions.append(cur)
            text = head.group(2).strip()
            # варианты после слитой строки относятся ко второму заданию,
            # первое остаётся без вариантов и отсеется в build()
            parts = GLUED.split(text)
            cur = {"n": int(head.group(1)), "q": parts[-1].strip(),
                   "options": [], "correct": []}
    if cur:
        questions.append(cur)
    return questions


def build(path=SOURCE):
    questions = []
    for item in read(path):
        options = [" ".join(o.split()) for o in item["options"] if o.strip()]
        text = " ".join(item["q"].split())
        correct = [i for i in item["correct"] if i < len(options)]
        options, correct = drop_repeats(options, correct)
        if len(text) < 10 or len(options) < 2:
            continue
        if not correct or len(correct) == len(options):
            continue
        questions.append({"q": text, "options": options,
                          "correct": sorted(correct), "tag": "verified"})

    return {SET_ID: {"id": SET_ID, "title": TITLE, "subject": SUBJECT,
                     "language": "ru", "questions": questions}}


if __name__ == "__main__":
    raw = read()
    data = build()[SET_ID]
    print(f"заданий в файле: {len(raw)}, на сайт попало: {len(data['questions'])}")
