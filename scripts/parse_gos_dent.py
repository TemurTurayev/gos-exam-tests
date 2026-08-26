#!/usr/bin/env python3
"""Разбор GOS.docx — банк вопросов по стоматологии.

Документ выгружен из тестовой системы и устроен строго:

    Задание #N
    Вопрос:
    <текст вопроса>
    Выберите один из 5 вариантов ответа:
    1) …  2) …  3) …  4) …  5) …

а в самом конце файла идёт ключ ко всем заданиям:

    N) (1 б.) Верные ответы: 1; 2;

Ключ здесь — главный источник ответа: он выгружен системой, а не проставлен
руками. Жёлтая подсветка вариантов в тексте служит проверкой — она совпала с
ключом в 1377 случаях из 1381, а в четырёх разошедшихся подсветка оказалась
неполной (отмечен один вариант из двух). Единственное задание без ключа
берётся по подсветке и помечается отдельным тегом.
"""
import re
import sys
from pathlib import Path

import docx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import ROOT

DOCX = ROOT / "sources" / "with_answers" / "GOS stomatologiya.docx"

SET_ID = "dent-gos-uz"
TITLE = "Стоматология — госэкзамен"
TITLE_UZ = "Stomatologiya — davlat imtihoni"
SUBJECT = "Стоматология"

TASK = re.compile(r"^Задание\s*#(\d+)\b")
OPTION = re.compile(r"^(\d+)\)\s*(.*)$")
KEY = re.compile(r"^(\d+)\)\s*\(\d+\s*б\.\)\s*Верные ответы:\s*(.+?)\s*$")
# доля подсвеченного текста в абзаце, начиная с которой вариант считается
# отмеченным: номер варианта иногда подсвечен, а иногда нет
MIN_HIGHLIGHT = 0.5


def highlighted(paragraph):
    runs = [r for r in paragraph.runs if r.text.strip()]
    if not runs:
        return False
    total = sum(len(r.text) for r in runs)
    marked = sum(len(r.text) for r in runs if r.font.highlight_color is not None)
    return marked / total >= MIN_HIGHLIGHT


def read(path=DOCX):
    """{номер задания: {q, options, marked}} и {номер: [индексы ответов]}."""
    document = docx.Document(str(path))
    tasks, answers = {}, {}
    number, mode = None, None

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        key = KEY.match(text)
        if key:
            answers[int(key.group(1))] = sorted(
                int(n) - 1 for n in re.findall(r"\d+", key.group(2)))
            continue

        head = TASK.match(text)
        if head:
            number = int(head.group(1))
            tasks[number] = {"q": "", "options": [], "marked": []}
            mode = None
            continue

        if number is None:
            continue
        if text == "Вопрос:":
            mode = "q"
            continue
        if text.startswith("Выберите"):
            mode = "options"
            continue

        option = OPTION.match(text)
        if option and mode == "options":
            tasks[number]["options"].append(option.group(2).strip())
            if highlighted(paragraph):
                tasks[number]["marked"].append(len(tasks[number]["options"]) - 1)
        elif mode == "q":
            tasks[number]["q"] = (tasks[number]["q"] + " " + text).strip()

    return tasks, answers


def build(path=DOCX):
    tasks, answers = read(path)
    questions = []

    for number in sorted(tasks):
        item = tasks[number]
        options = [" ".join(o.split()) for o in item["options"] if o.strip()]
        text = " ".join(item["q"].split())
        # ключ из системы, иначе подсветка в тексте
        correct = answers.get(number) or item["marked"]
        correct = [i for i in correct if i < len(options)]

        if len(text) < 8 or len(options) < 2 or len(set(options)) != len(options):
            continue
        if not correct or len(correct) == len(options):
            continue

        questions.append({
            "q": text, "options": options, "correct": sorted(correct),
            "tag": "verified" if number in answers else "marked",
        })

    return {SET_ID: {"id": SET_ID, "title": TITLE, "subject": SUBJECT,
                     "language": "uz", "questions": questions}}


if __name__ == "__main__":
    tasks, answers = read()
    agree = sum(1 for n, a in answers.items()
                if n in tasks and a == sorted(tasks[n]["marked"]))
    data = build()[SET_ID]
    tags = {}
    for q in data["questions"]:
        tags[q["tag"]] = tags.get(q["tag"], 0) + 1
    print(f"заданий в файле: {len(tasks)}, ключей: {len(answers)}, "
          f"ключ сошёлся с подсветкой: {agree}")
    print(f"{SET_ID}: {len(data['questions'])} вопросов, {tags}")
