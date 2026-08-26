#!/usr/bin/env python3
"""Сборка всех данных сайта: data/*.json и manifest.json.

Объединяет два источника наборов:
  * parse.build_core   — файлы с размеченным ответом (теги verified/disputed);
  * build_extra.build  — файлы без обычной разметки (marked/restored/ai/disputed).
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import DATA, build_core
from build_extra import build as build_extra
from parse_medx import build as build_medx
from fixes import apply_all as apply_fixes

TAG_ORDER = ["verified", "marked", "restored", "ai", "disputed"]

SUBJECTS_UZ = {
    "Педиатрия": "Pediatriya",
    "Детская хирургия": "Bolalar xirurgiyasi",
    "Терапия": "Terapiya",
    "Хирургия": "Xirurgiya",
    "Акушерство и гинекология": "Akusherlik va ginekologiya",
}

TITLES_UZ = {
    "ped-ambulator-ru": "Pediatriya — ambulator-poliklinika",
    "ped-1000-uz": "Pediatriya — 1000 test",
    "ped-1000-2-uz": "Pediatriya — kengaytirilgan bank",
    "ped-facult-ru": "Fakultet pediatriyasi",
    "ped-uz-lat": "Pediatriya — savollar banki",
    "ped-ru-sources": "Pediatriya — manbalari bilan",
    "child-surg-hospital-uz": "Gospital bolalar xirurgiyasi",
    "child-surg-ru": "Bolalar xirurgiyasi",
    "child-surg-facult-uz": "Fakultet bolalar xirurgiyasi",
    "child-surg-uz-lat": "Bolalar xirurgiyasi — savollar banki",
    "child-surg-hosp-ru2": "Gospital bolalar xirurgiyasi — manbalari bilan",
    "child-surg-ru-bank": "Bolalar xirurgiyasi — savollar ro‘yxati",
    "therapy-internal-ru": "Ichki kasalliklar",
    "therapy-1000-uz": "Terapiya — 1000 test",
    "therapy-ecg-ru": "Terapiya — EKG va kardiologiya",
    "therapy-table-ru": "Terapiya — mavzular bo‘yicha",
    "therapy-test-ru": "Fakultet terapiyasi",
    "therapy-ru-bank": "Terapiya — katta baza",
    "therapy-medx-uz": "Terapiya — ordinatura (MedXAcademy)",
    "surg-facult-ru": "Fakultet xirurgiyasi",
    "surg-hospital-ru": "Gospital xirurgiyasi",
    "surg-1000-uz": "Xirurgiya — 1000 test",
    "obgyn-ru": "Akusherlik va ginekologiya",
}


def dedupe(questions):
    """Убирает точные повторы: тот же вопрос с теми же вариантами и ответом.

    Вопрос с тем же текстом, но другими вариантами — это другой вопрос
    исходника, его оставляем.
    """
    seen, out = set(), []
    for q in questions:
        sig = (q["q"], tuple(q["options"]), tuple(q["correct"]))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(q)
    return out


# Наборы, снятые с публикации. Разбор и исходники остаются на месте — чтобы
# вернуть набор, достаточно убрать его отсюда и пересобрать сайт.
RETIRED = {
    "surg-hospital-ru": "материал неактуален (просьба от 26.08.2026)",
    "surg-facult-ru": "материал неактуален (просьба от 26.08.2026)",
}


def main():
    sets = {**build_core(), **build_extra(), **build_medx()}
    for sid in RETIRED:
        sets.pop(sid, None)
    for data in sets.values():
        data["questions"] = dedupe(data["questions"])

    # ручные правки ответов поверх разбора (data/answer_fixes.json)
    report = apply_fixes(sets)
    if report["проблемы"]:
        print("ПРАВКИ НЕ ПРИМЕНИЛИСЬ:")
        for line in report["проблемы"]:
            print("  " + line)
        sys.exit(1)

    manifest = []
    totals = Counter()
    for sid, data in sets.items():
        tags = Counter(q["tag"] for q in data["questions"])
        totals.update(tags)
        data["title_uz"] = TITLES_UZ.get(sid, data["title"])
        data["subject_uz"] = SUBJECTS_UZ.get(data["subject"], data["subject"])
        (DATA / f"{sid}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest.append({
            "id": sid, "title": data["title"], "subject": data["subject"],
            "title_uz": TITLES_UZ.get(sid, data["title"]),
            "subject_uz": SUBJECTS_UZ.get(data["subject"], data["subject"]),
            "language": data["language"], "count": len(data["questions"]),
            "tags": {t: tags[t] for t in TAG_ORDER if tags[t]},
        })

    manifest.sort(key=lambda m: (m["subject"], m["language"], m["title"]))
    (DATA / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    for m in manifest:
        print(f"{m['id']:24s} {m['language']}  {m['count']:5d}  {m['tags']}")
    print(f"\nВсего вопросов: {sum(m['count'] for m in manifest)}")
    print("По тегам:", {t: totals[t] for t in TAG_ORDER if totals[t]})
    print("Ручные правки:", {k: v for k, v in report.items() if k != "проблемы"})


if __name__ == "__main__":
    main()
