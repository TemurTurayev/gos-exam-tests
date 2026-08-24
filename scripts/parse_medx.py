#!/usr/bin/env python3
"""Разбор PDF «Terapiya 675 MedXAcademy».

Отличие от остальных PDF в двух вещах.

Ключ. Правильный вариант не написан текстом и не помечен аннотацией: страницы
собраны так, что каждый символ нарисован отдельной заливкой, а выделение ответа
— это жёлтые прямоугольники поверх строки. Поэтому ключ снимается не из
annots(), а из get_drawings(): берутся заливки цвета #FFFF00 и сопоставляются
со строками вариантов. Считается доля метки, попавшая в строку (а не наоборот):
метка узкая, строка длинная, и обратное отношение всегда было бы близко к нулю.

Пояснения. У 98 вопросов автор оставил строку «Izoh: …» — разбор кладёт её в
поле note, сайт показывает её после ответа.
"""
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import ROOT

PDF = ROOT / "sources" / "with_answers" / "Terapiya 675 MedXAcademy.pdf"

SET_ID = "therapy-medx-uz"
TITLE = "Терапия — ординатура (MedXAcademy)"
TITLE_UZ = "Terapiya — ordinatura (MedXAcademy)"
SUBJECT = "Терапия"

YELLOW = (1.0, 1.0, 0.0)
QUESTION = re.compile(r"^(\d{1,4})\.\s+(.*)$")
NOTE = re.compile(r"^Izoh\b[:.]?\s*(.*)$", re.I)
# доля жёлтого прямоугольника, попавшая в строку варианта
MIN_COVER = 0.5


def area(rect):
    return abs(rect.width * rect.height)


def page_lines(page):
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text:
                out.append((fitz.Rect(line["bbox"]), text))
    return out


def yellow_marks(page):
    marks = []
    for shape in page.get_drawings():
        fill = shape.get("fill")
        if fill and tuple(round(c, 3) for c in fill) == YELLOW:
            marks.append(fitz.Rect(shape["rect"]))
    return marks


def covered(box, mark):
    """Какая часть метки лежит внутри строки."""
    inter = box & mark
    if not inter or inter.is_empty:
        return 0.0
    return area(inter) / max(area(mark), 1e-6)


def read(path=PDF):
    """Сырые вопросы: номер, текст, варианты, помеченные индексы, пояснение."""
    doc = fitz.open(str(path))
    questions, cur = [], None

    for page in doc:
        marks = yellow_marks(page)
        # координаты страниц одинаковые, поэтому сверять со свежими метками
        # можно только строки этой же страницы: вопрос часто начинается внизу
        # одной страницы, а варианты продолжаются на следующей
        here = {}
        for rect, text in page_lines(page):
            head = QUESTION.match(text)
            if head:
                if cur:
                    questions.append(cur)
                cur = {"n": int(head.group(1)), "q": head.group(2),
                       "options": [], "boxes": [], "marked": set(), "note": ""}
                here = {}
            elif cur is None:
                continue
            elif NOTE.match(text):
                cur["note"] = NOTE.match(text).group(1)
            elif text.startswith("-"):
                cur["options"].append(text[1:].strip())
                cur["boxes"].append(rect)
                here[len(cur["options"]) - 1] = rect
            elif cur["note"]:
                cur["note"] += " " + text
            elif cur["options"]:
                cur["options"][-1] += " " + text
                cur["boxes"][-1] = cur["boxes"][-1] | rect
                last = len(cur["options"]) - 1
                here[last] = here[last] | rect if last in here else rect
            else:
                cur["q"] += " " + text

            for i, box in here.items():
                if any(covered(box, m) >= MIN_COVER for m in marks):
                    cur["marked"].add(i)

    if cur:
        questions.append(cur)
    return questions


def build(path=PDF):
    """Набор в формате сайта. Вопрос без единственной метки — «спорный»."""
    questions = []
    for item in read(path):
        options = [" ".join(o.split()) for o in item["options"] if o.strip()]
        text = " ".join(item["q"].split())
        marked = sorted(i for i in item["marked"] if i < len(options))
        if len(text) < 12 or len(options) < 2 or len(set(options)) != len(options):
            continue
        if not marked:
            continue
        q = {"q": text, "options": options, "correct": marked,
             "tag": "marked" if len(marked) == 1 else "disputed"}
        if item["note"]:
            q["note"] = " ".join(item["note"].split())
        questions.append(q)

    return {SET_ID: {"id": SET_ID, "title": TITLE, "subject": SUBJECT,
                     "language": "uz", "questions": questions}}


if __name__ == "__main__":
    data = build()[SET_ID]
    tags = {}
    for q in data["questions"]:
        tags[q["tag"]] = tags.get(q["tag"], 0) + 1
    notes = sum(1 for q in data["questions"] if q.get("note"))
    print(f"{SET_ID}: {len(data['questions'])} вопросов, {tags}, пояснений: {notes}")
