#!/usr/bin/env python3
"""Сопоставление вопросов между файлами.

Один и тот же вопрос встречается в разных исходниках: где-то с размеченным
ответом, где-то без. Часть узбекских файлов набрана кириллицей, часть —
латиницей, поэтому оба варианта приводятся к общему латинскому виду.
"""
import hashlib
import re
from difflib import SequenceMatcher

# узбекская и русская кириллица -> латиница
TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h", "ә": "a", "ө": "o",
}


def key(text):
    """Ключ для сравнения: латиница, без пунктуации, регистра и апострофов."""
    s = text.lower().replace("’", "").replace("'", "").replace("ʻ", "").replace("`", "")
    s = "".join(TRANSLIT.get(ch, ch) for ch in s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return " ".join(s.split())


def bucket(k, words=4):
    return " ".join(k.split()[:words])


class Index:
    """Индекс проверенных вопросов: ключ -> список правильных ответов."""

    def __init__(self):
        self.answers = {}
        self.buckets = {}

    def add(self, question, correct_texts):
        k = key(question)
        if len(k) < 15:
            return
        self.answers.setdefault(k, set()).update(key(t) for t in correct_texts)
        self.buckets.setdefault(bucket(k), []).append(k)

    def lookup(self, question, threshold=0.9):
        k = key(question)
        if k in self.answers:
            return self.answers[k]
        best, score = None, 0.0
        for cand in self.buckets.get(bucket(k), ()):
            r = SequenceMatcher(None, k, cand).ratio()
            if r > score:
                best, score = cand, r
        return self.answers[best] if score >= threshold else None


def resolve(options, answer_keys):
    """Индексы вариантов, совпавших с известными правильными ответами."""
    hits = []
    for i, opt in enumerate(options):
        ok = key(opt)
        if not ok:
            continue
        if ok in answer_keys:
            hits.append(i)
            continue
        # ответ мог быть записан с другой пунктуацией или сокращением
        for a in answer_keys:
            if len(a) > 12 and (a in ok or ok in a):
                hits.append(i)
                break
    return hits


def qhash(text):
    """Стабильный идентификатор вопроса — переживает переразбор файла."""
    return hashlib.md5(key(text).encode("utf-8")).hexdigest()[:10]
