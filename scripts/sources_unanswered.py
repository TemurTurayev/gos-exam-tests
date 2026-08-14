#!/usr/bin/env python3
"""Разбор шести исходников, в которых правильный ответ не размечен.

Возвращает вопросы в том же виде, что и основной парсер, но без ключа:
{"q": ..., "options": [...]}. Ключ добавляется отдельно — переносом из
проверенной базы, правилом «верен первый вариант» или ответом ИИ.
"""
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import ROOT, lines_of, convert_doc_to_docx, bold_ratio

NO_ANS = ROOT / "sources" / "without_answers"


def pdf_lines(path):
    doc = fitz.open(str(path))
    return lines_of("\n".join(p.get_text() for p in doc))


def _clean(items, min_opts=2, max_opts=6):
    out = []
    for q in items:
        text = " ".join(q["q"].split())
        opts = [" ".join(o.split()) for o in q["options"] if o.strip()]
        if len(text) < 12 or not (min_opts <= len(opts) <= max_opts):
            continue
        if len(set(opts)) != len(opts):
            continue
        out.append({"q": text, "options": opts})
    return out


def parse_dash(path):
    """«N. Вопрос» жирным, варианты строками «- текст» (узбекская латиница)."""
    out, cur = [], None
    for l in pdf_lines(path):
        if re.match(r"^\d{1,4}\.\s", l):
            if cur:
                out.append(cur)
            cur = {"q": re.sub(r"^\d+\.\s*", "", l), "options": []}
        elif l.startswith("-"):
            if cur:
                cur["options"].append(l[1:].strip())
        elif cur:
            if cur["options"]:
                cur["options"][-1] += " " + l
            else:
                cur["q"] += " " + l
    if cur:
        out.append(cur)
    return _clean(out)


def parse_number_line(path):
    """Номер вопроса отдельной строкой либо в начале строки с текстом.

    В этом PDF первые ~100 вопросов пронумерованы отдельной строкой, а дальше
    номер стоит на одной строке с вопросом — обрабатываем оба варианта.
    Вариантов ответа всегда четыре, поэтому последние четыре строки блока и
    есть варианты.
    """
    blocks, cur, last = [], None, 0
    for l in pdf_lines(path):
        m = re.match(r"^(\d{1,4})(?:\s+(\S.*))?$", l)
        if m and last < int(m.group(1)) < last + 10:
            if cur:
                blocks.append(cur)
            last = int(m.group(1))
            cur = [m.group(2)] if m.group(2) else []
        elif cur is not None:
            cur.append(l)
    if cur:
        blocks.append(cur)

    out = []
    for b in blocks:
        if len(b) < 5 or len(b) > 9:
            continue
        out.append({"q": " ".join(b[:-4]), "options": b[-4:]})
    return _clean(out)


def parse_header_block(path):
    """«№N … Уровень сложности – X», затем вопрос и варианты."""
    out, cur, wait = [], None, False
    header = re.compile(r"^№\s*\d|Уровень сложности|Источник|Глава\s*[–-]|стр[-\s]*\d")
    for l in pdf_lines(path):
        if header.search(l):
            if cur:
                out.append(cur)
            cur, wait = None, True
            continue
        if wait:
            cur, wait = {"q": l, "options": []}, False
        elif cur is not None:
            cur["options"].append(l)
    if cur:
        out.append(cur)
    return _clean(out)


def parse_bold_question(path):
    """Вопрос выделен жирным, варианты — обычные абзацы."""
    import docx
    conv = convert_doc_to_docx(path, ROOT / "scripts" / "_docx_conv")
    out, cur = [], None
    for p in docx.Document(str(conv)).paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if bold_ratio(p) > 0.5:
            if cur:
                out.append(cur)
            cur = {"q": t, "options": []}
        elif cur is not None:
            cur["options"].append(t)
    if cur:
        out.append(cur)
    return _clean(out)


# id набора -> описание источника без ключа
SOURCES = [
    dict(id="child-surg-uz-lat", file="102-bol-hirurgia-test-sajt-uzb-495 (1).pdf",
         parser=parse_dash, title="Детская хирургия — банк вопросов",
         subject="Детская хирургия", language="uz"),
    dict(id="ped-uz-lat", file="Pediatriya javob 98%aniq 99.pdf",
         parser=parse_dash, title="Педиатрия — банк вопросов",
         subject="Педиатрия", language="uz"),
    dict(id="child-surg-ru-bank", file="bolalar xirurgiyasi rus.pdf",
         parser=parse_number_line, title="Детская хирургия — перечень вопросов",
         subject="Детская хирургия", language="ru"),
    dict(id="child-surg-hosp-ru2", file="Детская хирургия....✓.pdf",
         parser=parse_header_block, title="Госпитальная детская хирургия — с источниками",
         subject="Детская хирургия", language="ru"),
    dict(id="ped-ru-sources", file="Пед рус...✓.pdf",
         parser=parse_header_block, title="Педиатрия — с источниками",
         subject="Педиатрия", language="ru"),
    dict(id="therapy-ru-bank", file="terapiya rus baza test.doc",
         parser=parse_bold_question, title="Терапия — большая база",
         subject="Терапия", language="ru"),
]


def load_all():
    result = {}
    for spec in SOURCES:
        path = NO_ANS / spec["file"]
        result[spec["id"]] = spec["parser"](path) if path.exists() else []
    return result


if __name__ == "__main__":
    for spec in SOURCES:
        qs = (NO_ANS / spec["file"]).exists() and spec["parser"](NO_ANS / spec["file"]) or []
        print(f"{spec['id']:22s} {len(qs):5d}  <- {spec['file']}")
