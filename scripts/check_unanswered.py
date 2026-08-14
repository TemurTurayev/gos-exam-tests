#!/usr/bin/env python3
"""Проверка гипотезы «в файлах без ключа правильный ответ — всегда первый».

Метод: находим вопросы, которые встречаются и в файле без ключа, и в наборе
с проверенным ответом. Для каждого совпадения смотрим, на какой позиции в
файле без ключа стоит заведомо правильный вариант. Если гипотеза верна,
позиция должна быть 0 почти всегда.
"""
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import ROOT, DATA, norm, textutil_txt, lines_of, convert_doc_to_docx

NO_ANS = ROOT / "sources" / "without_answers"


def pdf_lines(path):
    doc = fitz.open(str(path))
    return lines_of("\n".join(p.get_text() for p in doc))


def parse_dash(path):
    """«N. Вопрос» + варианты строками «- текст» (узбекские PDF)."""
    out, cur = [], None
    for l in pdf_lines(path):
        if re.match(r"^\d{1,4}\.\s", l):
            if cur and len(cur["options"]) >= 2:
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
    if cur and len(cur["options"]) >= 2:
        out.append(cur)
    return out


def parse_plain_num(path):
    """«N   Вопрос» + варианты обычными строками (bolalar xirurgiyasi rus)."""
    out, cur = [], None
    expect = 1
    for l in pdf_lines(path):
        m = re.match(r"^(\d{1,4})\s+(.*)$", l)
        if m and expect <= int(m.group(1)) < expect + 5 and m.group(2).strip():
            if cur and len(cur["options"]) >= 2:
                out.append(cur)
            cur = {"q": m.group(2).strip(), "options": []}
            expect = int(m.group(1)) + 1
        elif cur is not None:
            cur["options"].append(l.strip())
    if cur and len(cur["options"]) >= 2:
        out.append(cur)
    return [q for q in out if 2 <= len(q["options"]) <= 6]


def parse_numbered_header(path):
    """«№N ... Уровень сложности – X» затем вопрос и 4 варианта."""
    out, cur, await_q = [], None, False
    for l in pdf_lines(path):
        if l.startswith("№") or "Уровень сложности" in l or "Источник" in l or "Глава" in l:
            if cur and len(cur["options"]) >= 2:
                out.append(cur)
            cur, await_q = None, True
            continue
        if await_q:
            cur = {"q": l.strip(), "options": []}
            await_q = False
        elif cur is not None:
            cur["options"].append(l.strip())
    if cur and len(cur["options"]) >= 2:
        out.append(cur)
    return [q for q in out if 2 <= len(q["options"]) <= 6]


def parse_bold_doc(path):
    """Вопрос выделен жирным, варианты — обычные строки (terapiya rus baza)."""
    import docx
    from parse import bold_ratio
    d = docx.Document(str(convert_doc_to_docx(path, ROOT / "scripts" / "_docx_conv")))
    out, cur = [], None
    for p in d.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if bold_ratio(p) > 0.5:
            if cur and len(cur["options"]) >= 2:
                out.append(cur)
            cur = {"q": t, "options": []}
        elif cur is not None:
            cur["options"].append(t)
    if cur and len(cur["options"]) >= 2:
        out.append(cur)
    return [q for q in out if 2 <= len(q["options"]) <= 6]


SOURCES = [
    ("102-bol-hirurgia-test-sajt-uzb-495 (1).pdf", parse_dash, "Детская хирургия (узб.)"),
    ("Pediatriya javob 98%aniq 99.pdf", parse_dash, "Педиатрия (узб.)"),
    ("bolalar xirurgiyasi rus.pdf", parse_plain_num, "Детская хирургия (рус.)"),
    ("Детская хирургия....✓.pdf", parse_numbered_header, "Госпитальная детская хирургия (рус.)"),
    ("Пед рус...✓.pdf", parse_numbered_header, "Педиатрия (рус.)"),
    ("terapiya rus baza test.doc", parse_bold_doc, "Терапия (рус.)"),
]


def build_reference():
    """нормализованный вопрос -> множество нормализованных правильных ответов"""
    ref = {}
    for f in DATA.glob("*.json"):
        if f.name == "manifest.json":
            continue
        for q in json.loads(f.read_text(encoding="utf-8"))["questions"]:
            key = norm(q["q"])
            if len(key) < 15:
                continue
            ref.setdefault(key, set()).update(norm(q["options"][i]) for i in q["correct"])
    return ref


def build_index(ref):
    """Индекс по первым словам вопроса — чтобы не сравнивать всё со всем."""
    idx = {}
    for k in ref:
        idx.setdefault(" ".join(k.split()[:4]), []).append(k)
    return idx


def find_match(key, ref, idx):
    if key in ref:
        return ref[key]
    # близкое совпадение ищем только среди вопросов с таким же началом
    best, best_score = None, 0.0
    for k in idx.get(" ".join(key.split()[:4]), ()):
        score = SequenceMatcher(None, key, k).ratio()
        if score > best_score:
            best, best_score = k, score
    return ref[best] if best_score >= 0.9 else None


def main():
    ref = build_reference()
    idx = build_index(ref)
    print(f"эталонных вопросов с проверенным ответом: {len(ref)}\n")

    for fname, parser, label in SOURCES:
        path = NO_ANS / fname
        if not path.exists():
            print(f"{fname}: файл не найден"); continue
        qs = parser(path)
        positions = Counter()
        matched = 0
        for q in qs:
            answers = find_match(norm(q["q"]), ref, idx)
            if not answers:
                continue
            opts = [norm(o) for o in q["options"]]
            hit = [i for i, o in enumerate(opts) if o in answers]
            if len(hit) == 1:
                positions[hit[0]] += 1
                matched += 1
        total = sum(positions.values())
        share = f"{100*positions[0]//total}%" if total else "—"
        print(f"{label:38s} вопросов={len(qs):4d}  сверено={matched:4d}  "
              f"позиция верного: {dict(sorted(positions.items()))}  доля первого: {share}")


if __name__ == "__main__":
    main()
