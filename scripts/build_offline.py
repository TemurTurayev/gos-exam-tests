#!/usr/bin/env python3
"""Собирает офлайн-версию одним файлом: gos-exam-tests-offline.html

Обычный index.html подгружает данные через fetch, а браузер запрещает это
для файлов, открытых с диска (file://). Поэтому для офлайна данные, стили и
скрипты вшиваются прямо в HTML — такой файл можно скинуть на флешку или
отправить в мессенджере, и он откроется двойным кликом без интернета.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "gos-exam-tests-offline.html"

SCRIPTS = ["js/i18n.js", "js/storage.js", "js/data.js", "js/ui.js", "js/app.js"]


def main():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    sets = {m["id"]: json.loads((DATA / f"{m['id']}.json").read_text(encoding="utf-8"))
            for m in manifest}
    embedded = json.dumps({"manifest": manifest, "sets": sets},
                          ensure_ascii=False, separators=(",", ":"))
    # </script> внутри данных разорвал бы тег
    embedded = embedded.replace("</", "<\\/")

    css = (ROOT / "style.css").read_text(encoding="utf-8")
    js = "\n\n".join((ROOT / s).read_text(encoding="utf-8") for s in SCRIPTS)
    total = sum(m["count"] for m in manifest)

    html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Гос экзамен — тесты (офлайн)</title>
<style>
{css}
</style>
</head>
<body>
<header class="topbar">
  <div class="topbar-inner">
    <a href="#/" class="brand"><span class="brand-mark">🩺</span> <span id="brandText">Гос экзамен</span></a>
    <div class="topbar-right">
      <div id="langSwitch" class="lang-switch"></div>
      <button id="userChip" class="user-chip" type="button" hidden></button>
      <div id="scoreBadge" class="score-badge" hidden></div>
    </div>
  </div>
</header>

<main id="app" class="app"></main>

<footer class="footer">
  <p id="footerText"></p>
  <p id="offlineLine">Офлайн-версия · {total} вопросов внутри файла</p>
</footer>

<script>window.EMBEDDED_DATA = {embedded};</script>
<script>
{js}
</script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    size = OUT.stat().st_size / 1024 / 1024
    print(f"{OUT.name}: {size:.1f} МБ, вопросов: {total}")


if __name__ == "__main__":
    main()
