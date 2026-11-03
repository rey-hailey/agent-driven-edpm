#!/usr/bin/env python3
"""산출물(md)을 공유용 문서로 내보낸다: 인쇄용 HTML(기본), PDF, Word(docx).

사용:
  python3 automation/scripts/edpm_export.py PRD.md                      # → 05.outputs/PRD_YYYYMMDD_HHMM.html
  python3 automation/scripts/edpm_export.py 03.docs/M.관리/M04_중간보고서.md --to pdf
  python3 automation/scripts/edpm_export.py 03.docs/2.정의/E06_상세요구사항서.md --to docx [--reference 회사양식.docx]
  python3 automation/scripts/edpm_export.py <md> --keep-examples       # 템플릿 예시 행을 지우지 않음

- html: 외부 의존성 없음. 표지(제목·판·날짜·상태), 목차, 표, 인쇄 시 쪽 번호. 브라우저 "PDF로 저장"으로도 PDF가 된다.
- pdf: Chrome·Chromium이 있으면 headless로 인쇄. 없으면 html을 만들고 안내한다.
- docx: pandoc이 있으면 변환(`--reference`로 회사 Word 양식의 스타일 적용). 없으면 html을 만들고 안내한다.
- frontmatter는 표지로 옮기고 본문에서는 뺀다. 작성 가이드(> **작성 가이드** 인용 블록)와 `(예시)`·`예시` 행은 기본으로 뺀다.
표준 라이브러리만 쓴다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("EDPM_ROOT") or Path(__file__).resolve().parents[2])
CHROME = [os.environ.get("CHROME", ""), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          "/Applications/Chromium.app/Contents/MacOS/Chromium", "google-chrome", "chromium", "chromium-browser"]

CSS = """
:root{--ink:#1f2937;--muted:#6b7280;--line:#d1d5db;--head:#f3f4f6;--accent:#1d4ed8}
*{box-sizing:border-box} body{font-family:-apple-system,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif;
color:var(--ink);line-height:1.65;max-width:900px;margin:0 auto;padding:32px 24px;font-size:15px}
h1{font-size:26px;border-bottom:2px solid var(--accent);padding-bottom:6px} h2{font-size:20px;margin-top:32px;border-bottom:1px solid var(--line);padding-bottom:4px}
h3{font-size:17px;margin-top:24px} table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}
th,td{border:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left} th{background:var(--head)}
code{background:var(--head);padding:1px 4px;border-radius:3px;font-size:90%} pre{background:var(--head);padding:12px;overflow:auto;border-radius:6px}
blockquote{border-left:3px solid var(--line);margin:12px 0;padding:4px 12px;color:var(--muted)}
.cover{border:1px solid var(--line);border-radius:8px;padding:20px 24px;margin-bottom:28px}
.cover h1{border:0;margin:0 0 8px} .cover .meta{color:var(--muted);font-size:13px}
.toc{font-size:13.5px;margin-bottom:28px} .toc ul{margin:4px 0 0 0;padding-left:18px}
@media print{body{padding:0;max-width:none} h2{page-break-after:avoid} table,pre{page-break-inside:avoid}
@page{margin:18mm 16mm 20mm;@bottom-center{content:counter(page) " / " counter(pages);font-size:10px;color:#6b7280}}}
"""


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    fm = {}
    for line in text[3:end].splitlines():
        line = re.sub(r"\s#(\s.*)?$", "", line).rstrip()
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm, text[end + 4:].lstrip("\n")


def strip_template(body: str, keep_examples: bool) -> str:
    out, skip_quote = [], False
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("> **작성 가이드**") or s.startswith("> **이 문서"):
            skip_quote = True
            continue
        if skip_quote:
            if s.startswith(">"):
                continue
            skip_quote = False
        if not keep_examples and s.startswith("|") and re.search(r"\|\s*(\(예시\)|예시[ :\]]|예시\s*\|)|\(예시\)", s):
            continue
        out.append(line)
    return "\n".join(out)


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1).split("/")[-1], s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md_to_html(body: str) -> tuple[str, list[tuple[int, str, str]]]:
    lines, out, toc, i = body.splitlines(), [], [], 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            cls = ' class="mermaid"' if lang == "mermaid" else ""
            out.append(f"<pre{cls}>{html.escape(chr(10).join(buf))}</pre>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lvl, title = len(m.group(1)), m.group(2)
            anchor = f"s{len(toc) + 1}"
            toc.append((lvl, title, anchor))
            out.append(f'<h{lvl} id="{anchor}">{inline(title)}</h{lvl}>')
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not set("".join(cells)) <= set("-: "):
                    rows.append(cells)
                i += 1
            if rows:
                head, *rest = rows
                out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                           + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rest) + "</tbody></table>")
            continue
        if re.match(r"^([-*]|\d+\.)\s+", s):
            tag = "ol" if re.match(r"^\d+\.", s) else "ul"
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i]))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip()); i += 1
            out.append("<blockquote>" + "<br>".join(inline(x) for x in buf if x) + "</blockquote>")
            continue
        if s in ("---", "***"):
            out.append("<hr>"); i += 1; continue
        if not s:
            i += 1; continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||```|>|[-*]\s|\d+\.\s)", lines[i].strip()):
            buf.append(lines[i].strip()); i += 1
        out.append(f"<p>{inline(' '.join(buf))}</p>")
    return "\n".join(out), toc


def build_html(src: Path, keep_examples: bool) -> str:
    fm, body = split_frontmatter(src.read_text(encoding="utf-8"))
    body = strip_template(body, keep_examples)
    content, toc = md_to_html(body)
    title = fm.get("title") or next((t for lvl, t, _ in toc if lvl == 1), src.stem)
    meta = " · ".join(x for x in [fm.get("doc_id", ""), fm.get("version", ""), f"상태 {fm['status']}" if fm.get("status") else "",
                                  f"갱신 {fm['updated']}" if fm.get("updated", "").strip("YMD-") else "", f"작성 {fm['owner']}" if fm.get("owner") else ""] if x)
    toc_html = "".join(f'<li style="margin-left:{(lvl - 2) * 14}px"><a href="#{a}">{inline(t)}</a></li>' for lvl, t, a in toc if lvl in (2, 3))
    mermaid = ('<script type="module">import m from "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs";m.initialize({startOnLoad:true});</script>'
               if 'class="mermaid"' in content else "")
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>"
            f'<div class="cover"><h1>{html.escape(title)}</h1><div class="meta">{html.escape(meta)}<br>출력 {dt.date.today()} · 원본 {html.escape(str(src))}</div></div>'
            + (f'<nav class="toc"><b>목차</b><ul>{toc_html}</ul></nav>' if toc_html else "")
            + content + mermaid + "</body></html>")


def find_chrome() -> str | None:
    for c in CHROME:
        if c and (Path(c).exists() or shutil.which(c)):
            return shutil.which(c) or c
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="산출물 md → html·pdf·docx")
    ap.add_argument("src", type=Path)
    ap.add_argument("--to", choices=["html", "pdf", "docx"], default="html")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "05.outputs")
    ap.add_argument("--reference", type=Path, help="docx: 스타일을 가져올 회사 Word 양식 (pandoc --reference-doc)")
    ap.add_argument("--keep-examples", action="store_true", help="템플릿 예시 행을 남김")
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    base = a.out_dir / f"{a.src.stem}_{stamp}"
    page = build_html(a.src, a.keep_examples)
    html_path = base.with_suffix(".html")
    html_path.write_text(page, encoding="utf-8")
    if a.to == "html":
        print(html_path); return 0
    if a.to == "pdf":
        chrome = find_chrome()
        if not chrome:
            print(f"Chrome을 찾지 못해 HTML만 만들었습니다: {html_path}\n브라우저로 열어 인쇄 → PDF로 저장하세요 (또는 CHROME 환경변수로 경로 지정).")
            return 0
        pdf = base.with_suffix(".pdf")
        r = subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                            f"--print-to-pdf={pdf}", html_path.as_uri()],
                           capture_output=True, text=True)
        if r.returncode != 0 or not pdf.exists():
            print(f"PDF 변환 실패, HTML을 쓰세요: {html_path}\n{r.stderr[-500:]}"); return 1
        print(pdf); return 0
    pandoc = shutil.which("pandoc")
    if not pandoc:
        print(f"pandoc이 없어 HTML만 만들었습니다: {html_path}\nWord가 필요하면 `brew install pandoc` 후 다시 실행하거나, Word에서 HTML을 열어 저장하세요.")
        return 0
    docx = base.with_suffix(".docx")
    cmd = [pandoc, str(html_path), "-f", "html", "-o", str(docx)]
    if a.reference:
        cmd += ["--reference-doc", str(a.reference)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"docx 변환 실패: {r.stderr[-500:]}"); return 1
    print(docx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
