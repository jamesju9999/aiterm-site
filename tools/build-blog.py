#!/usr/bin/env python3
"""把 Medium 文章的 Markdown 原稿轉成 blog/ 底下的靜態頁面。

網站本身刻意維持純 HTML/CSS/JS（GitHub Pages 直接吃，沒有建置步驟），
所以這支腳本產生的 HTML 是**要 commit 進 repo 的**——它是作者手邊的工具，
不是網站的相依。新增或修改文章之後跑一次：

    python3 tools/build-blog.py

原稿目錄由 SOURCE 指定，預設是作者本機的 BlogContent。原稿不在的話直接
中止而不是產出半套東西——安靜地少掉幾篇比報錯更難發現。
"""

import html
import os
import re
import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get(
    "BLOG_SOURCE",
    Path.home() / "Documents/BlogContent/Medium/AITERM",
))
OUT = SITE / "blog"

# 每篇文章的網址代號與兩種語言的原稿檔名。
#
# 刻意寫死而不是從資料夾名推導：網址一旦公開就不該因為某天改了資料夾名稱
# 就跟著變。新增文章時在這裡加一列。
#
# `medium_zh` / `medium_en` 是這篇在 Medium 上的原文網址。留 None 代表
# 還沒發佈——那時候頁尾就不會出現連結，不會生出一個指向空白的按鈕。
ARTICLES = [
    {
        "slug": "work-still-needs-organizing",
        "dir": "ArrangeAITask",
        "zh": "AI再厲害，工作還是得有人安排.md",
        "en": "however-good-ai-gets-work-still-needs-organizing.md",
        "date": "2026-09-06",
        "medium_zh": None,
        "medium_en": None,
    },
    {
        "slug": "chatgpt-web-bridge",
        "dir": "ChatGPT Bridge",
        "zh": "chatgpt網頁橋接.md",
        "en": "chatgpt-web-bridge.md",
        "date": "2026-08-13",
        "medium_zh": None,
        "medium_en": None,
    },
    {
        "slug": "knowledge-base-rag",
        "dir": "知識庫",
        "zh": "aiterm-knowledge-base-decisions.md",
        "en": None,          # 這篇只有中文版
        "date": "2026-08-03",
        "medium_zh": None,
        "medium_en": None,
    },
    {
        "slug": "loop-engineering",
        "dir": "Loop Engineering",
        "zh": "loopstudio-循環工程.md",
        "en": "loopstudio-loop-engineering.md",
        "date": "2026-07-16",
        "medium_zh": None,
        "medium_en": None,
    },
    {
        "slug": "database-natural-language",
        "dir": "NatureLangAndDatabase",
        "zh": "ai資料庫自然語言查詢.md",
        "en": "ai-database-natural-language.md",
        "date": "2026-07-15",
        "medium_zh": None,
        "medium_en": None,
    },
]

T = {
    "zh": {
        "lang": "zh-Hant",
        "blog": "文章",
        "blog_title": "文章",
        "blog_sub": "AITerm 開發過程中的設計決策與實作筆記",
        "back": "← 回到文章列表",
        "home": "首頁",
        "other": ("EN", "en.html"),
        "read": "閱讀全文 →",
        "medium": "在 Medium 上閱讀原文 →",
        "only_zh": "（本篇僅有中文版）",
        "site_title": "AITerm 文章",
        "nav": [("工作看板", "../index.html#taskboard"), ("功能", "../index.html#features"),
                ("安裝", "../index.html#install")],
    },
    "en": {
        "lang": "en",
        "blog": "Blog",
        "blog_title": "Writing",
        "blog_sub": "Design decisions and implementation notes from building AITerm",
        "back": "← All posts",
        "home": "Home",
        "other": ("中文", "index.html"),
        "read": "Read →",
        "medium": "Read the original on Medium →",
        "only_zh": "",
        "site_title": "AITerm Blog",
        "nav": [("Task Board", "../en.html#taskboard"), ("Features", "../en.html#features"),
                ("Install", "../en.html#install")],
    },
}

LOGO = '<a href="../index.html" class="nav-logo"><span class="logo-bracket">[</span>AI<span class="logo-term">Term</span><span class="logo-bracket">]</span></a>'


# ── Markdown ───────────────────────────────────────────────────────────────

def inline(s: str) -> str:
    """行內語法。先跳脫 HTML 再套用，原稿裡的 < > 才不會變成標籤。"""
    s = html.escape(s, quote=False)
    # 先處理 code：裡面的 * 不該被當成粗體
    parts = re.split(r"(`[^`]+`)", s)
    for i, p in enumerate(parts):
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            parts[i] = f"<code>{p[1:-1]}</code>"
            continue
        p = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                   r'<a href="\2" target="_blank" rel="noopener">\1</a>', p)
        p = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", p)
        p = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", p)
        parts[i] = p
    return "".join(parts)


def md_to_html(md: str, img_prefix: str) -> tuple[str, str, str]:
    """回傳 (標題, 副標, 內文 HTML)。標題與副標會從內文移除，由版型另外排。"""
    lines = md.split("\n")
    title, subtitle = "", ""
    out, i = [], 0
    in_list = None
    in_fence = False
    fence: list[str] = []

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    while i < len(lines):
        line = lines[i].rstrip()

        if line.startswith("```"):
            if in_fence:
                out.append("<pre><code>" + html.escape("\n".join(fence)) + "</code></pre>")
                fence, in_fence = [], False
            else:
                close_list()
                in_fence = True
            i += 1
            continue
        if in_fence:
            fence.append(lines[i])
            i += 1
            continue

        if not title and line.startswith("# "):
            title = line[2:].strip()
            i += 1
            continue
        if title and not subtitle and re.fullmatch(r"\*[^*].*\*", line):
            subtitle = line[1:-1].strip()
            i += 1
            continue

        m = re.match(r"^(#{2,6}) (.+)$", line)
        if m:
            close_list()
            lv = len(m.group(1))
            out.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>")
            i += 1
            continue

        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line)
        if m:
            close_list()
            src = m.group(2)
            if src.startswith("images/"):
                src = img_prefix + src[len("images/"):]
            out.append(
                f'<figure><img src="{html.escape(src)}" alt="{html.escape(m.group(1))}" loading="lazy">'
                f"</figure>"
            )
            i += 1
            continue

        if re.fullmatch(r"-{3,}", line):
            close_list()
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^\s*[-*] (.+)$", line)
        if m:
            if in_list != "ul":
                close_list()
                out.append("<ul>")
                in_list = "ul"
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        m = re.match(r"^\s*\d+\. (.+)$", line)
        if m:
            if in_list != "ol":
                close_list()
                out.append("<ol>")
                in_list = "ol"
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        if not line.strip():
            close_list()
            i += 1
            continue

        # 段落：連續的非空行合併成一段
        close_list()
        buf = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{1,6} |!\[|-{3,}$|```|\s*[-*] |\s*\d+\. )", lines[i]
        ):
            buf.append(lines[i].rstrip())
            i += 1
        out.append("<p>" + inline(" ".join(buf) if _latin(buf) else "".join(buf)) + "</p>")

    close_list()
    return title, subtitle, "\n".join(out)


def _latin(buf: list[str]) -> bool:
    """英文段落換行要補空白，中文不能補——補了會在句中多出空隙。"""
    text = "".join(buf)
    cjk = len(re.findall(r"[一-鿿]", text))
    return cjk < len(text) * 0.15


# ── 版型 ───────────────────────────────────────────────────────────────────

def page(lang: str, title: str, desc: str, body: str, canonical: str) -> str:
    t = T[lang]
    nav = "".join(f'<li><a href="{u}">{n}</a></li>' for n, u in t["nav"])
    other_label, other_href = t["other"]
    return f"""<!DOCTYPE html>
<html lang="{t['lang']}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(desc)}" />
  <link rel="canonical" href="https://aiterm.win/blog/{canonical}" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{html.escape(title)}" />
  <meta property="og:description" content="{html.escape(desc)}" />
  <meta property="og:url" content="https://aiterm.win/blog/{canonical}" />
  <meta property="og:image" content="https://aiterm.win/og-image.png" />
  <link rel="icon" href="../icon.png" />
  <link rel="stylesheet" href="../style.css" />
  <link rel="stylesheet" href="blog.css" />
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      {LOGO}
      <ul class="nav-links">
        <li><a href="{'index.html' if lang == 'zh' else 'en.html'}">{t['blog']}</a></li>
        {nav}
        <li><a href="{other_href}">{other_label}</a></li>
        <li><a href="https://github.com/jamesju9999/AITERM" target="_blank" rel="noopener" class="nav-github">GitHub</a></li>
      </ul>
    </div>
  </nav>
{body}
  <footer class="footer">
    <div class="container">
      <p>© 2026 AITerm · Apache 2.0 · <a href="https://github.com/jamesju9999/AITERM" target="_blank" rel="noopener">GitHub</a></p>
    </div>
  </footer>
</body>
</html>
"""


def main() -> int:
    if not SOURCE.is_dir():
        print(f"找不到原稿目錄：{SOURCE}", file=sys.stderr)
        return 1

    OUT.mkdir(exist_ok=True)
    (OUT / "images").mkdir(exist_ok=True)
    cards: dict[str, list[str]] = {"zh": [], "en": []}
    urls: list[str] = []

    for art in ARTICLES:
        src_dir = SOURCE / art["dir"]
        img_dir = OUT / "images" / art["slug"]
        if (src_dir / "images").is_dir():
            shutil.rmtree(img_dir, ignore_errors=True)
            shutil.copytree(src_dir / "images", img_dir)

        for lang in ("zh", "en"):
            name = art[lang]
            if not name:
                continue
            md_path = src_dir / name
            if not md_path.is_file():
                print(f"缺少原稿：{md_path}", file=sys.stderr)
                return 1
            title, subtitle, body = md_to_html(
                md_path.read_text(encoding="utf-8"),
                f"images/{art['slug']}/",
            )
            fname = f"{art['slug']}.html" if lang == "zh" else f"{art['slug']}-en.html"
            mu = art.get(f"medium_{lang}")
            medium = (
                f'      <p class="post-medium"><a href="{mu}" target="_blank" '
                f'rel="noopener">{T[lang]["medium"]}</a></p>'
            ) if mu else ""
            article = f"""  <article class="post">
    <div class="post-inner">
      <a class="post-back" href="{'index.html' if lang == 'zh' else 'en.html'}">{T[lang]['back']}</a>
      <h1 class="post-title">{inline(title)}</h1>
      <div class="post-meta">{art['date']}</div>
      {f'<p class="post-sub">{inline(subtitle)}</p>' if subtitle else ''}
      <div class="post-body">
{body}
      </div>
{medium}
    </div>
  </article>
"""
            (OUT / fname).write_text(
                page(lang, f"{title} — AITerm", subtitle or title, article, fname),
                encoding="utf-8",
            )
            urls.append(f"blog/{fname}")
            cards[lang].append(f"""        <a class="post-card" href="{fname}">
          <div class="post-card-date">{art['date']}</div>
          <h2>{inline(title)}</h2>
          <p>{inline(subtitle)}</p>
          <span class="post-card-more">{T[lang]['read']}</span>
        </a>""")

    for lang in ("zh", "en"):
        t = T[lang]
        listing = f"""  <section class="section post-list">
    <div class="container">
      <h1 class="section-title">{t['blog_title']}</h1>
      <p class="section-sub">{t['blog_sub']}</p>
      <div class="post-grid">
{chr(10).join(cards[lang])}
      </div>
    </div>
  </section>
"""
        fname = "index.html" if lang == "zh" else "en.html"
        (OUT / fname).write_text(
            page(lang, f"{t['site_title']}", t["blog_sub"], listing, fname),
            encoding="utf-8",
        )
        urls.append(f"blog/{fname}")

    write_sitemap(urls)
    print(f"產生 {len(urls)} 頁 + sitemap.xml：")
    for u in sorted(urls):
        print("  ", u)
    return 0


def write_sitemap(blog_urls: list[str]) -> None:
    """整份 sitemap 由這裡產生，含首頁。

    刻意不是「附加到既有檔案」：手動維護的話，新增文章時一定會忘記更新，
    而漏掉的頁面不會有任何錯誤訊息。整份重寫才不會漂移。
    """
    alt = ('    <xhtml:link rel="alternate" hreflang="zh-Hant" href="https://aiterm.win/"/>\n'
           '    <xhtml:link rel="alternate" hreflang="en" href="https://aiterm.win/en.html"/>\n'
           '    <xhtml:link rel="alternate" hreflang="x-default" href="https://aiterm.win/"/>')
    rows = [f"  <url>\n    <loc>https://aiterm.win/</loc>\n{alt}\n  </url>",
            f"  <url>\n    <loc>https://aiterm.win/en.html</loc>\n{alt}\n  </url>"]
    for u in sorted(blog_urls):
        rows.append(f"  <url>\n    <loc>https://aiterm.win/{u}</loc>\n  </url>")
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(rows) + "\n</urlset>\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
