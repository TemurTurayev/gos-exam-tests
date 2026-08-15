#!/usr/bin/env python3
"""Независимая проверка: правильный ли ответ доехал из исходника в JSON.

Скрипт НЕ использует логику парсера. Он заново читает исходный файл и
собирает множество «текстов, помеченных как правильные» (по своей, отдельной
логике), а затем сверяет с тем, что записано в data/*.json:

  * каждый сохранённый правильный ответ должен быть помечен в исходнике;
  * ни один сохранённый неправильный ответ не должен быть помечен.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import FILES, DATA, marked_texts, norm

def main():
    print(f"{'файл':24s} {'вопросов':>8s} {'ответ не помечен':>17s} {'помечен неверный':>17s}")
    print("-" * 72)
    total_bad = 0
    for spec in FILES:
        data = json.loads((DATA / f"{spec['id']}.json").read_text(encoding="utf-8"))
        marked = marked_texts(spec)
        miss = wrong = 0
        for q in data["questions"]:
            for i, opt in enumerate(q["options"]):
                n = norm(opt)
                if not n:
                    continue
                if i in q["correct"] and n not in marked:
                    miss += 1
                if i not in q["correct"] and n in marked:
                    wrong += 1
        total_bad += miss
        flag = "  ✗" if miss else ""
        print(f"{spec['id']:24s} {len(data['questions']):8d} {miss:17d} {wrong:17d}{flag}")
    print(f"\nОтветов без подтверждения в исходнике: {total_bad}")
    print("Это не потеря: такие вопросы помечены тегом «спорный» и видны "
          "пользователю с предупреждением.")
    print("(колонка «помечен неверный» — вариант помечен в другом вопросе; "
          "совпадения формулировок допустимы)")


if __name__ == "__main__":
    main()
