#!/usr/bin/env python3
"""Извлечение ключа из PDF, где правильный ответ выделен маркером.

В двух узбекских файлах ответ не написан текстом, а подсвечен жёлтым
(аннотация Highlight) или подчёркнут. Аннотация хранит точные четырёхугольники
выделения, поэтому вариант определяется по пересечению этих квадратов со
строкой варианта, а не по общей рамке аннотации: рамка часто захватывает
соседние строки.
"""
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import ROOT

NO_ANS = ROOT / "sources" / "without_answers"

HIGHLIGHT, UNDERLINE = 8, 9


def annot_rects(annot):
    """Точные прямоугольники выделения (по quadpoints), иначе рамка целиком."""
    pts = annot.vertices
    if pts and len(pts) % 4 == 0:
        out = []
        for i in range(0, len(pts), 4):
            quad = pts[i:i + 4]
            xs = [p[0] for p in quad]
            ys = [p[1] for p in quad]
            out.append(fitz.Rect(min(xs), min(ys), max(xs), max(ys)))
        return out
    return [annot.rect]


def overlap_ratio(line_rect, mark_rect):
    inter = line_rect & mark_rect
    if not inter or inter.is_empty:
        return 0.0
    return inter.get_area() / max(line_rect.get_area(), 1e-6)


def parse_with_highlights(path, min_overlap=0.25):
    """Вопросы вида «N. текст» с вариантами «- текст» и ключом из выделений."""
    doc = fitz.open(str(path))
    questions = []
    cur = None

    for page in doc:
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).strip()
                if text:
                    lines.append((fitz.Rect(line["bbox"]), text))

        marks = []
        for a in (page.annots() or []):
            if a.type[0] in (HIGHLIGHT, UNDERLINE):
                marks.append((a.type[0], annot_rects(a)))

        for rect, text in lines:
            if re.match(r"^\d{1,4}\.\s", text):
                if cur:
                    questions.append(cur)
                cur = {"q": re.sub(r"^\d+\.\s*", "", text), "options": [],
                       "boxes": [], "marked": {}}
            elif text.startswith("-") and cur is not None:
                cur["options"].append(text[1:].strip())
                cur["boxes"].append(rect)
            elif cur is not None:
                # перенос строки: продолжение варианта либо самого вопроса
                if cur["options"]:
                    cur["options"][-1] += " " + text
                    cur["boxes"][-1] = cur["boxes"][-1] | rect
                else:
                    cur["q"] += " " + text

            if cur is None:
                continue
            # какие варианты этой страницы попали под выделение
            for kind, rects in marks:
                for i, box in enumerate(cur["boxes"]):
                    best = max((overlap_ratio(box, r) for r in rects), default=0.0)
                    if best >= min_overlap:
                        prev = cur["marked"].get(i, 0.0)
                        # подчёркивание слабее заливки: учитываем с меньшим весом
                        weight = best if kind == HIGHLIGHT else best * 0.5
                        cur["marked"][i] = max(prev, weight)

    if cur:
        questions.append(cur)
    return questions


def finalize(questions):
    """Оставляет вопросы с одним уверенно выделенным вариантом."""
    ready, disputed, empty = [], [], []
    for q in questions:
        opts = [" ".join(o.split()) for o in q["options"] if o.strip()]
        text = " ".join(q["q"].split())
        if len(text) < 12 or not (2 <= len(opts) <= 6) or len(set(opts)) != len(opts):
            continue
        marks = {i: v for i, v in q["marked"].items() if i < len(opts)}
        item = {"q": text, "options": opts}
        if not marks:
            empty.append(item)
            continue
        top = max(marks.values())
        # выделение нередко захватывает и соседнюю строку: если второй вариант
        # закрыт почти так же сильно, вопрос честнее пометить спорным
        winners = [i for i, v in marks.items() if v >= top * 0.55]
        if len(winners) == 1:
            ready.append({**item, "correct": winners})
        else:
            disputed.append({**item, "correct": sorted(winners)})
    return ready, disputed, empty


if __name__ == "__main__":
    for name in ["Pediatriya javob 98%aniq 99.pdf",
                 "102-bol-hirurgia-test-sajt-uzb-495 (1).pdf"]:
        qs = parse_with_highlights(NO_ANS / name)
        ready, disputed, empty = finalize(qs)
        print(f"{name[:42]:44s} всего={len(qs):4d} "
              f"с ключом={len(ready):4d} спорных={len(disputed):3d} без метки={len(empty):4d}")
