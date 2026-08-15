#!/usr/bin/env python3
"""Разбор шести исходников, в которых правильный ответ не размечен.

Возвращает вопросы в том же виде, что и основной парсер, но без ключа:
{"q": ..., "options": [...]}. Ключ добавляется отдельно — переносом из
проверенной базы, правилом «верен первый вариант» или ответом ИИ.

Главная сложность этих PDF — переносы строк. Длинный вопрос занимает две
строки, и без склейки его «хвост» превращается в отдельный вариант ответа
(а по правилу «верен первый вариант» ещё и становится правильным). Строки
склеиваются по правому краю: если строка дотянулась до края текстового
блока, следующая строка — её продолжение.
"""
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import ROOT, lines_of, convert_doc_to_docx, bold_ratio

NO_ANS = ROOT / "sources" / "without_answers"

# на сколько пунктов строка может не дотянуть до правого края и всё ещё
# считаться «полной» (перенос по словам редко оставляет больше)
WRAP_TOLERANCE = 20


def page_lines(page):
    """Строки страницы: (x0, x1, текст)."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text:
                out.append((line["bbox"][0], line["bbox"][2], text))
    return out


def join_wrapped(lines, margin):
    """Склеивает перенесённые строки: полная строка + продолжение = одна."""
    joined = []
    for x0, x1, text in lines:
        if joined and joined[-1][1] >= margin - WRAP_TOLERANCE:
            prev_x0, _, prev_text = joined[-1]
            joined[-1] = (prev_x0, x1, prev_text + " " + text)
        else:
            joined.append((x0, x1, text))
    return joined


def right_margin(pages, percentile=0.95):
    """Правый край текста по всему документу.

    Берём не максимум, а 95-й процентиль: в этих PDF попадаются одиночные
    строки заметно правее основного текста (колонтитулы, длинные заголовки),
    и по максимуму настоящий край текста определяется неверно.
    """
    xs = sorted(x1 for lines in pages for _, x1, _ in lines)
    if not xs:
        return 0
    return xs[min(len(xs) - 1, int(len(xs) * percentile))]


def pdf_lines(path):
    """Плоский список строк документа с уже склеенными переносами."""
    doc = fitz.open(str(path))
    pages = [page_lines(page) for page in doc]
    margin = right_margin(pages)
    out = []
    for lines in pages:
        out += [t for _, _, t in join_wrapped(lines, margin)]
    return out


def _clean(items, min_opts=2, max_opts=6):
    out = []
    for q in items:
        text = " ".join(q["q"].split())
        opts = [" ".join(o.split()) for o in q["options"] if o.strip()]
        if len(text) < 12 or not (min_opts <= len(opts) <= max_opts):
            continue
        if len(set(opts)) != len(opts):
            continue
        # вариант, заканчивающийся двоеточием или вопросительным знаком, —
        # это не ответ, а хвост неправильно разрезанного вопроса
        if any(o.rstrip().endswith((":", "?")) for o in opts):
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

    После склейки переносов в блоке остаются вопрос и ровно четыре варианта,
    поэтому последние четыре строки блока и есть варианты.
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
        # если вопрос занял две строки, он заканчивается двоеточием или
        # вопросительным знаком — иначе считаем, что вариантов ровно четыре
        end = next((i for i, l in enumerate(b) if l.rstrip().endswith((":", "?"))), None)
        if end is None or end > len(b) - 2:
            end = len(b) - 5
        out.append({"q": " ".join(b[:end + 1]), "options": b[end + 1:]})
    return _clean(out)


HEADER = re.compile(r"^№\s*\d|Уровень сложности|Источник|Глава\s*[–-]|стр[-\s]*\d")


def parse_header_block(path):
    """«№N … Уровень сложности – X», затем вопрос и варианты.

    Заголовок опознаётся по тексту, а не по отступу: в разных файлах он то
    сдвинут, то стоит вровень с вопросом.
    """
    blocks, cur = [], None
    for l in pdf_lines(path):
        if HEADER.search(l):
            if cur:
                blocks.append(cur)
            cur = []
            continue
        if cur is not None:
            cur.append(l)
    if cur:
        blocks.append(cur)

    out = []
    for b in blocks:
        if len(b) < 3:
            continue
        # вопрос заканчивается строкой с двоеточием или вопросительным знаком;
        # если её нет — считаем, что вариантов четыре
        end = next((i for i, l in enumerate(b) if l.rstrip().endswith((":", "?"))), None)
        if end is None or end > len(b) - 2:
            if not (5 <= len(b) <= 8):
                continue
            end = len(b) - 5
        out.append({"q": " ".join(b[:end + 1]), "options": b[end + 1:]})
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
        path = NO_ANS / spec["file"]
        qs = spec["parser"](path) if path.exists() else []
        print(f"{spec['id']:22s} {len(qs):5d}  <- {spec['file']}")
