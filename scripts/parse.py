#!/usr/bin/env python3
"""Parse the 16 source test files (with known answer keys) into unified JSON."""
import json
import re
import subprocess
from pathlib import Path

import docx
import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "with_answers"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

LETTER_LABEL = re.compile(
    r"^\s*[#@*]*\s*\d*[\.\)]?\s*[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ]{1,2}[\.\)]\s*", re.UNICODE
)
QNUM = re.compile(r"^\s*\*?\s*\d+[\.\)]\s*")


def clean_option(text, strip_leading_hash=False):
    t = text.strip()
    if strip_leading_hash and t.startswith("#"):
        t = t[1:].strip()
    t = LETTER_LABEL.sub("", t, count=1)
    t = t.rstrip("*").strip()
    return t


def textutil_txt(path: Path) -> str:
    out = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True, text=True,
    )
    return out.stdout


def lines_of(text):
    return [l for l in (x.strip() for x in text.splitlines()) if l]


# ---------- Format A: "#question" / "+correct" / "-wrong" ----------
def parse_format_a(lines):
    questions = []
    cur = None
    for l in lines:
        if l.startswith("#"):
            if cur and cur["options"]:
                questions.append(cur)
            cur = {"q": l[1:].strip(), "options": [], "correct": None}
        elif l.startswith("+"):
            if cur is None:
                continue
            cur["correct"] = len(cur["options"])
            cur["options"].append(l[1:].strip().rstrip("*").strip())
        elif l.startswith("-"):
            if cur is None:
                continue
            cur["options"].append(l[1:].strip().rstrip("*").strip())
        else:
            # continuation of question text (wrapped line)
            if cur is not None and not cur["options"]:
                cur["q"] += " " + l
    if cur and cur["options"]:
        questions.append(cur)
    return questions


# ---------- Format B: docx table [difficulty, question, correct, wrong, wrong, wrong] ----------
def parse_format_b(path):
    d = docx.Document(str(path))
    questions = []
    for t in d.tables:
        rows = t.rows
        header_skipped = False
        for r in rows:
            cells = [c.text.strip() for c in r.cells]
            if not header_skipped:
                header_skipped = True
                if "Тесты" in cells[1] or "тест" in cells[1].lower():
                    continue
            if len(cells) < 3 or not cells[1]:
                continue
            q = cells[1]
            correct = cells[2]
            wrongs = [c for c in cells[3:] if c]
            if not correct:
                continue
            options = [correct] + wrongs
            questions.append({"q": q, "options": options, "correct": 0})
    return questions


# ---------- Format C: "*N. question" / "#opt" correct / "letter." wrong / "@x" ignore ----------
def parse_format_c(lines):
    questions = []
    cur = None
    for l in lines:
        if QNUM.match(l) and l.lstrip().startswith("*"):
            if cur and cur["options"]:
                questions.append(cur)
            q_text = QNUM.sub("", l, count=1).strip()
            cur = {"q": q_text, "options": [], "correct": None}
        elif l.startswith("@"):
            continue
        elif l.startswith("#"):
            if cur is None:
                continue
            cur["correct"] = len(cur["options"])
            cur["options"].append(clean_option(l, strip_leading_hash=True))
        elif LETTER_LABEL.match(l):
            if cur is None:
                continue
            cur["options"].append(clean_option(l))
        else:
            if cur is not None and not cur["options"]:
                cur["q"] += " " + l
    if cur and cur["options"]:
        questions.append(cur)
    return questions


# ---------- Format D: "N. question" / option lines, correct ends with "*" ----------
def parse_format_d(lines):
    questions = []
    cur = None
    for l in lines:
        if QNUM.match(l) and not l.lstrip().startswith("*"):
            if cur and cur["options"]:
                questions.append(cur)
            q_text = QNUM.sub("", l, count=1).strip()
            cur = {"q": q_text, "options": [], "correct": None}
        elif LETTER_LABEL.match(l) or (cur and cur["q"] and l):
            if cur is None:
                continue
            is_correct = l.rstrip().endswith("*")
            opt = clean_option(l)
            if is_correct:
                cur["correct"] = len(cur["options"])
            cur["options"].append(opt)
    if cur and cur["options"]:
        questions.append(cur)
    return questions


# ---------- Format E: bullet question "•" / options "*A) correct" or "A) wrong" ----------
BULLET = re.compile(r"^[••]\s*")


def parse_format_e(lines):
    questions = []
    cur = None
    for l in lines:
        is_bullet_q = bool(BULLET.match(l))
        is_num_q = bool(QNUM.match(l)) and not l.lstrip().startswith("*")
        if is_bullet_q or is_num_q:
            if cur and cur["options"]:
                questions.append(cur)
            q_text = BULLET.sub("", l).strip()
            q_text = QNUM.sub("", q_text, count=1).strip()
            cur = {"q": q_text, "options": [], "correct": None}
        else:
            if cur is None:
                continue
            is_correct = l.lstrip().startswith("*")
            opt = clean_option(l)
            if not opt:
                continue
            if is_correct:
                cur["correct"] = len(cur["options"])
            cur["options"].append(opt)
    if cur and cur["options"]:
        questions.append(cur)
    return questions


# ---------- Format F: bold run marks correct answer (needs .doc -> .docx conversion) ----------
def parse_format_f(docx_path):
    d = docx.Document(str(docx_path))
    questions = []
    cur = None
    for p in d.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        is_bold = any(r.bold for r in p.runs if r.text.strip())
        is_qstart = bool(QNUM.match(text))
        if is_qstart:
            if cur and cur["options"]:
                questions.append(cur)
            q_text = QNUM.sub("", text, count=1).strip()
            cur = {"q": q_text, "options": [], "correct": None}
            continue
        if cur is None:
            continue
        if LETTER_LABEL.match(text) or len(cur["options"]) > 0 or True:
            opt = clean_option(text)
            if not opt:
                continue
            if is_bold:
                cur["correct"] = len(cur["options"])
            cur["options"].append(opt)
    if cur and cur["options"]:
        questions.append(cur)
    return questions


# ---------- Format G: PDF "Правильный ответ: X. text" then options ----------
def parse_format_g(path):
    doc = fitz.open(str(path))
    full_text = "\n".join(page.get_text() for page in doc)
    lines = lines_of(full_text)
    questions = []
    cur = None
    correct_letter = None
    correct_text = None
    for l in lines:
        m = re.match(r"^Правильный ответ:\s*([A-ZА-ЯЁ])\.\s*(.*)$", l)
        if m:
            correct_letter, correct_text = m.group(1), m.group(2).strip()
            continue
        if re.match(r"^\d+\.\s", l):
            if cur and cur["options"]:
                # resolve correct index
                if correct_letter:
                    for i, o in enumerate(cur["options"]):
                        if o.startswith(correct_letter + ".") or o == correct_text:
                            cur["correct"] = i
                            break
                questions.append(cur)
            q_text = re.sub(r"^\d+\.\s*", "", l)
            cur = {"q": q_text, "options": [], "correct": None}
            correct_letter, correct_text = None, None
            continue
        if LETTER_LABEL.match(l) and cur is not None:
            label_m = re.match(r"^([A-ZА-ЯЁ])[\.\)]", l)
            letter = label_m.group(1) if label_m else None
            opt = clean_option(l)
            idx = len(cur["options"])
            cur["options"].append(opt)
            if correct_letter and letter == correct_letter:
                cur["correct"] = idx
        elif cur is not None and not cur["options"]:
            cur["q"] += " " + l
    if cur and cur["options"]:
        if correct_letter:
            for i, o in enumerate(cur["options"]):
                if o == correct_text:
                    cur["correct"] = i
                    break
        questions.append(cur)
    return questions


def finalize(questions, min_options=2):
    out = []
    for q in questions:
        if q["correct"] is None:
            continue
        # drop empty options, remapping the correct index by position
        options = q["options"]
        if q["correct"] >= len(options):
            continue
        kept = [(i, o) for i, o in enumerate(options) if o.strip()]
        new_correct = next((j for j, (i, o) in enumerate(kept) if i == q["correct"]), None)
        if new_correct is None:
            continue
        q["options"] = [o for _, o in kept]
        q["correct"] = new_correct
        if len(q["options"]) < min_options:
            continue
        if not q["q"].strip():
            continue
        out.append(q)
    return out


FILES = [
    dict(id="ped-ambulator-ru", title="Педиатрия — Амбулаторно-поликлиническая (рус.)",
         subject="Педиатрия", language="ru", fmt="a",
         file="Ambulator-poliklinik pediatriya RUS.txt"),
    dict(id="ped-1000-uz", title="Педиатрия — 1000 тестов (узб.)",
         subject="Педиатрия", language="uz", fmt="a",
         file="pediatriya 1000 full.txt"),
    dict(id="child-surg-hospital-uz", title="Госпитальная детская хирургия (узб.)",
         subject="Детская хирургия", language="uz", fmt="c",
         file="Госпитал болалар хирургияси.doc"),
    dict(id="child-surg-ru", title="Детская хирургия (рус.)",
         subject="Детская хирургия", language="ru", fmt="f",
         file="Детская хирургия.doc"),
    dict(id="therapy-internal-ru", title="Внутренние болезни (рус.)",
         subject="Терапия", language="ru", fmt="c",
         file="Ички касалликлар (Рус).doc"),
    dict(id="ped-1000-2-uz", title="Педиатрия — тесты (узб., docx)",
         subject="Педиатрия", language="uz", fmt="d",
         file="Педиатрия-1000.docx"),
    dict(id="therapy-1000-uz", title="Терапия — 1000 тестов (узб.)",
         subject="Терапия", language="uz", fmt="f",
         file="Терапия - 1000.doc"),
    dict(id="therapy-ecg-ru", title="Терапия — ЭКГ и кардиология (рус.)",
         subject="Терапия", language="ru", fmt="g",
         file="Терапия ....✓.pdf"),
    dict(id="therapy-table-ru", title="Терапия — тесты по темам (рус.)",
         subject="Терапия", language="ru", fmt="b",
         file="Терапия русс с ответами.docx"),
    dict(id="therapy-test-ru", title="Терапия — тест (рус.)",
         subject="Терапия", language="ru", fmt="a_doc",
         file="Терапия тест.doc"),
    dict(id="surg-facult-ru", title="Факультетская хирургия (рус.)",
         subject="Хирургия", language="ru", fmt="d",
         file="Фак. хирургия.doc"),
    dict(id="child-surg-facult-uz", title="Факультетская детская хирургия (узб.)",
         subject="Детская хирургия", language="uz", fmt="c",
         file="Факультет_болалар_хирургияси_Рус.doc"),
    dict(id="surg-hospital-ru", title="Госпитальная хирургия (рус.)",
         subject="Хирургия", language="ru", fmt="a_docx",
         file="Хирургия тест.docx"),
    dict(id="obgyn-ru", title="Акушерство и гинекология (рус.)",
         subject="Акушерство и гинекология", language="ru", fmt="d",
         file="акушерлик ва гинекология рус.doc"),
    dict(id="ped-facult-ru", title="Факультетская педиатрия (рус.)",
         subject="Педиатрия", language="ru", fmt="e",
         file="педиатрия  рус.doc"),
    dict(id="surg-1000-uz", title="Хирургия — 1000 тестов (узб.)",
         subject="Хирургия", language="uz", fmt="f",
         file="хирургия - 1000.doc"),
]


def load_docx_paragraph_texts(path):
    d = docx.Document(str(path))
    return [p.text for p in d.paragraphs]


def convert_doc_to_docx(doc_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["textutil", "-convert", "docx", "-output",
         str(out_dir / (doc_path.stem + ".docx")), str(doc_path)],
        capture_output=True, text=True,
    )
    return out_dir / (doc_path.stem + ".docx")


def main():
    conv_dir = ROOT / "scripts" / "_docx_conv"
    manifest = []
    for spec in FILES:
        path = SRC / spec["file"]
        fmt = spec["fmt"]
        if fmt == "a":
            text = path.read_text(encoding="utf-8-sig") if path.suffix == ".txt" else textutil_txt(path)
            qs = parse_format_a(lines_of(text))
        elif fmt == "a_doc":
            text = textutil_txt(path)
            qs = parse_format_a(lines_of(text))
        elif fmt == "a_docx":
            texts = load_docx_paragraph_texts(path)
            qs = parse_format_a([t.strip() for t in texts if t.strip()])
        elif fmt == "b":
            qs = parse_format_b(path)
        elif fmt == "c":
            text = textutil_txt(path)
            qs = parse_format_c(lines_of(text))
        elif fmt == "d":
            if path.suffix == ".docx":
                texts = [t.strip() for t in load_docx_paragraph_texts(path) if t.strip()]
            else:
                texts = lines_of(textutil_txt(path))
            qs = parse_format_d(texts)
        elif fmt == "e":
            text = textutil_txt(path)
            qs = parse_format_e(lines_of(text))
        elif fmt == "f":
            docx_path = convert_doc_to_docx(path, conv_dir)
            qs = parse_format_f(docx_path)
        elif fmt == "g":
            qs = parse_format_g(path)
        else:
            raise ValueError(fmt)

        qs = finalize(qs)
        out = {
            "id": spec["id"],
            "title": spec["title"],
            "subject": spec["subject"],
            "language": spec["language"],
            "questions": qs,
        }
        out_path = DATA / f"{spec['id']}.json"
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest.append({
            "id": spec["id"], "title": spec["title"], "subject": spec["subject"],
            "language": spec["language"], "count": len(qs),
        })
        print(f"{spec['id']:28s} {len(qs):5d} questions   <- {spec['file']}")

    (DATA / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("\nTotal:", sum(m["count"] for m in manifest))


if __name__ == "__main__":
    main()
