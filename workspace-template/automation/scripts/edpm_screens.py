#!/usr/bin/env python3
"""EdPM 화면 지도: E10의 화면 목록·상태·화면별 구성으로 모든 화면을 한 장에 (.edpm/screens.html), 그리고
실무형 화면설계서(sb-lowfi)의 입력 md를 만든다.

사용:
  python3 automation/scripts/edpm_screens.py            # 화면 지도 만들기
  python3 automation/scripts/edpm_screens.py --open     # 만들고 브라우저로 열기
  python3 automation/scripts/edpm_screens.py --json     # 데이터만 출력 (점검용)
  python3 automation/scripts/edpm_screens.py --sb-md [경로]  # sb-lowfi 입력 화면설계서.md (기본 05.outputs/화면설계서.md)
  python3 automation/scripts/edpm_screens.py --archive <릴리스> [--base <URL>] [--capture]
                                                          # 릴리스 화면 아카이브: 05.outputs/화면아카이브/<릴리스>_<날짜>/
                                                          # (index.md + 화면별 PNG 자리, --capture는 Playwright가 있으면 직접 캡처)

역할 분담: 화면 지도는 전체 목록·빠진 상태·끊긴 이동을 점검하는 용도(자동, 저충실도). 보여주는 화면설계서
(메타 표·번호 마커·Description·상태·처리 규칙, HTML·PPTX·Figma)는 --sb-md로 만든 md를 sb-lowfi-pptx 스킬이
화면별로 그린다. sb-lowfi 결과 HTML이 05.outputs/에 있으면 화면 지도가 화면마다 그 화면으로 링크한다.

화면마다 프로토타입을 만들지 않는다. 화면 전체는 E10에서 자동으로 그리고(저충실도 프레임·상태 탭·설명·화면 이동),
높은 충실도의 프로토타입은 PRD 9절의 정수에만 쓴다 (V 트랙). 원천은 E10 하나이며, 문서를 고치면 다시 만든다
(edpm_dashboard.py가 함께 만들므로 세션 시작·저장 훅으로 갱신된다).

E10 8절 "화면별 구성" 형식 (화면마다 블록 하나):
  ### SCR-004 오답 코칭
  - 진입: SCR-003 채점 결과에서 "다시 생각해 보기"
  - 상단: 문항 3/10 · 진행 막대
  - 본문: 내 풀이(단계별) · 처음 틀린 단계 강조 · 힌트 카드
  - 하단: [힌트 더 보기] · [다시 풀기 → SCR-003] · (입력: 질문)
  - 설명: 정답은 시도 전에 보이지 않음 (GR-01)
  - 연결: F-012 · AC-1~AC-5
진입·설명·연결 외의 키는 위에서 아래로 놓이는 영역이다. 항목은 " · "로 나누며 [라벨 → SCR-ID]는 화면 이동 버튼,
[라벨]은 버튼, (입력: 라벨)은 입력칸, 그 밖은 표시 요소다.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edpm_check as ck  # noqa: E402

ROOT = ck.ROOT
OUT = ROOT / ".edpm" / "screens.html"
TEMPLATE = Path(__file__).resolve().parent / "screens_template.html"
STATES = ["빈 상태", "로딩", "오류", "동의 없음", "오프라인", "권한 없음"]
META = {"진입", "설명", "연결"}
SCR = re.compile(r"SCR-\d{2,4}")


def _is_example(cells_or_line) -> bool:
    t = " ".join(cells_or_line) if isinstance(cells_or_line, list) else cells_or_line
    return "(예시)" in t or "{" in t or t.strip().startswith("예시")


def parse_items(text: str) -> list[dict]:
    out = []
    for raw in [x.strip() for x in re.split(r"\s+·\s+", text) if x.strip()]:
        m = re.fullmatch(r"\[(.+?)\s*(?:→|->)\s*(SCR-\d{2,4})\s*\]", raw)
        if m:
            out.append({"t": "nav", "label": m.group(1).strip(), "to": m.group(2)})
            continue
        m = re.fullmatch(r"\[(.+?)\]", raw)
        if m:
            out.append({"t": "btn", "label": m.group(1).strip()})
            continue
        m = re.fullmatch(r"\((?:입력|input)\s*:\s*(.+?)\)", raw)
        if m:
            out.append({"t": "input", "label": m.group(1).strip()})
            continue
        out.append({"t": "text", "label": raw})
    return out


def parse_e10(text: str) -> dict:
    screens: dict[str, dict] = {}

    def get(sid):
        return screens.setdefault(sid, {"id": sid, "name": "", "role": "", "purpose": "", "f": [], "la": "", "platform": "",
                                        "priority": "", "areas": [], "entry": "", "desc": "", "links": [], "states": {}, "url": "",
                                        "a11y": [], "has_layout": False})

    for r in ck._table_rows(text, "2. 화면 목록"):
        if not r or _is_example(r) or not SCR.fullmatch(r[0]):
            continue
        s = get(r[0])
        cols = (r + [""] * 8)[:8]
        s.update({"name": cols[1], "role": cols[2], "purpose": cols[3], "f": re.findall(r"F-\d{3}", cols[4]),
                  "la": cols[5], "platform": cols[6], "priority": cols[7]})
    for r in ck._table_rows(text, "3. 화면별 핵심 상태"):
        if not r or _is_example(r) or not SCR.fullmatch(r[0]):
            continue
        s = get(r[0])
        for name, val in zip(STATES, (r + [""] * 7)[1:7]):
            if ck._filled(val):
                s["states"][name] = val
    for r in ck._table_rows(text, "5. 접근성 메모"):
        if not r or _is_example(r) or not SCR.fullmatch(r[0]):
            continue
        get(r[0])["a11y"].append({"item": r[1] if len(r) > 1 else "", "req": r[2] if len(r) > 2 else ""})
    # 8절 화면별 구성
    cur = None
    in8 = False
    for ln in text.splitlines():
        if ln.startswith("## "):
            in8 = "화면별 구성" in ln
            cur = None
            continue
        if not in8:
            continue
        if ln.startswith("###"):
            cur = None  # 제목을 만나면 앞 블록은 끝 (템플릿 블록 {SCR-0NN}이 앞 화면에 붙지 않게)
        m = re.match(r"^###\s+(SCR-\d{2,4})\s*(.*)$", ln)
        if m:
            cur = None if _is_example(ln) else get(m.group(1))
            if cur is not None:
                cur["has_layout"] = True
                if m.group(2).strip() and not cur["name"]:
                    cur["name"] = m.group(2).strip()
            continue
        if cur is None:
            continue
        m = re.match(r"^\s*-\s*([^:：]+)[:：]\s*(.+)$", ln)
        if not m or "{" in ln:
            continue
        key, val = m.group(1).strip(), m.group(2).strip()
        if key == "진입":
            cur["entry"] = val
        elif key == "주소":
            cur["url"] = val.strip("`")
        elif key == "설명":
            cur["desc"] = (cur["desc"] + " " + val).strip()
        elif key == "연결":
            cur["links"] = [x.strip() for x in re.split(r"\s*[·,]\s*", val) if x.strip()]
            cur["f"] = sorted(set(cur["f"]) | set(re.findall(r"F-\d{3}", val)))
        else:
            cur["areas"].append({"key": key, "items": parse_items(val)})
    # IA 흐름(1절 Mermaid): 노드 라벨의 SCR-ID로 이어진 화면
    flows = []
    ia = text.split("## 1.", 1)[-1].split("## 2.", 1)[0] if "## 1." in text else ""
    node = {m.group(1): m.group(2) for m in re.finditer(r"(\w+)\[\"?[^\]\"]*?(SCR-\d{2,4})[^\]]*\]", ia)}
    for m in re.finditer(r"(\w+)(?:\[[^\]]*\])?\s*-->\s*(\w+)", ia):
        a, b = node.get(m.group(1)), node.get(m.group(2))
        if a and b and a in screens and b in screens:  # 실제 화면 목록에 있는 것만 (예시 IA는 걸러짐)
            flows.append([a, b])
    return {"screens": screens, "flows": flows}


def build() -> dict:
    docs = ck.load_docs()
    e10 = ck.find(docs, "E10")
    ctx = ck.agents_context()
    base = {"generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "product": ctx.get("회사·제품", ""),
            "e10": None, "screens": [], "flows": [], "summary": {}}
    if e10 is None:
        return base
    data = parse_e10(ck.read(e10["path"]))
    screens = data["screens"]
    incoming: dict[str, list[str]] = {k: [] for k in screens}
    broken = []
    for s in screens.values():
        outs = sorted({it["to"] for a in s["areas"] for it in a["items"] if it["t"] == "nav"})
        s["out"] = outs
        for t in outs:
            if t in incoming:
                incoming[t].append(s["id"])
            else:
                broken.append(f"{s['id']} → {t}")
        for t in SCR.findall(s["entry"]):
            if t in screens and t != s["id"]:
                incoming[s["id"]].append(t)
    for s in screens.values():
        s["in"] = sorted(set(incoming.get(s["id"], [])))
        s["missing_states"] = [x for x in STATES if x not in s["states"]]
        warns = []
        if not s["has_layout"]:
            warns.append("화면별 구성 없음 (8절)")
        if s["missing_states"]:
            warns.append("상태 빠짐: " + ", ".join(s["missing_states"]))
        if not s["f"]:
            warns.append("연결 기능(F) 없음")
        if not s["role"]:
            warns.append("화면 목록(2절)에 없음")
        s["warns"] = warns
    roles = []
    for s in screens.values():  # E10 2절 화면 목록에 처음 나온 순서
        if s["role"] not in roles:
            roles.append(s["role"])
    order = sorted(screens.values(), key=lambda s: (roles.index(s["role"]) if s["role"] else 99, s["id"]))
    base.update({
        "sb_html": latest_sb_html(),
        "e10": {"status": e10["status"], "rel": e10["rel"], "url": _editor_url() + e10["path"].resolve().as_posix()},
        "screens": order, "flows": data["flows"], "broken": broken,
        "summary": {"screens": len(order), "with_layout": sum(1 for s in order if s["has_layout"]),
                    "missing_states": sum(1 for s in order if s["missing_states"]), "broken": len(broken),
                    "warns": sum(1 for s in order if s["warns"])},
    })
    return base


PLATFORM = [("모바일", "Mobile"), ("태블릿", "Mobile (태블릿)"), ("웹", "PC"), ("PC", "PC")]


def to_sb_md(data: dict) -> str:
    """sb-lowfi-pptx 입력 형식: ### <ID>. 화면명 + 메타 표 + 레이아웃 + UI 컴포넌트 + 상태별 화면 + 처리 규칙."""
    plat = lambda p: next((v for k, v in PLATFORM if k in (p or "")), p or "-")  # noqa: E731
    L = [f"# 화면설계서 — {data.get('product') or '제품'}", "",
         f"> E10 화면·정보구조설계서에서 자동 생성 ({data['generated']}). 고칠 때는 E10을 고치고 다시 만듭니다: "
         "`python3 automation/scripts/edpm_screens.py --sb-md`. 이 파일을 입력으로 `sb-lowfi-pptx` 스킬이 화면을 그립니다.", "",
         "## 화면 목록", "", "| Screen ID | 화면명 | 역할 | 플랫폼 | 우선순위 |", "|-----------|--------|------|--------|----------|"]
    L += [f"| {s['id']} | {s['name']} | {s['role'] or '-'} | {plat(s['platform'])} | {s['priority'] or 'P1'} |" for s in data["screens"]]
    names = {s["id"]: s["name"] for s in data["screens"]}
    for s in data["screens"]:
        L += ["", f"### {s['id']}. {s['name'] or s['id']}", "", "| 항목 | 내용 |", "|------|------|",
              f"| URL | {s['entry'] or '-'} |", f"| 플랫폼 | {plat(s['platform'])} |", f"| 접근 권한 | {s['role'] or '-'} |",
              f"| 관련 기능 | {' · '.join(dict.fromkeys(s['f'] + s['links'])) or '-'} |", "| 관련 API | - |"]
        if s["purpose"]:
            L += ["", f"목적: {s['purpose']}"]
        if s["areas"]:
            L += ["", "**레이아웃 (위에서 아래)**", "", "```"]
            L += [f"[{a['key']}] " + " | ".join(("[" + i["label"] + "]") if i["t"] in ("nav", "btn") else
                                              ("(" + i["label"] + ")") if i["t"] == "input" else i["label"] for i in a["items"]) for a in s["areas"]]
            L += ["```", "", "**UI 컴포넌트**", "", "| No. | 컴포넌트 | 설명·인터랙션 |", "|-----|----------|---------------|"]
            n = 0
            for a in s["areas"]:
                for i in a["items"]:
                    n += 1
                    how = {"nav": f"버튼. 누르면 {i.get('to')} {names.get(i.get('to'), '')}(으)로 이동".rstrip(),
                           "btn": "버튼", "input": "입력칸", "text": "표시"}[i["t"]]
                    L.append(f"| {n} | {a['key']}: {i['label']} | {how} |")
        else:
            L += ["", "> 화면별 구성(E10 8절)이 아직 없습니다. 레이아웃과 UI 컴포넌트를 E10에 먼저 씁니다."]
        if s["states"]:
            L += ["", "**상태별 화면**", "", "| 상태 | 조건 | 표시 내용 |", "|------|------|-----------|"]
            L += [f"| {k} | - | {v} |" for k, v in s["states"].items()]
        rules = [x.strip() for x in re.split(r"(?<=[.다])\s+", s["desc"]) if x.strip()] if s["desc"] else []
        rules += [f"접근성 — {a['item']}: {a['req']}" for a in s["a11y"]]
        if s["missing_states"]:
            rules.append("정의되지 않은 상태: " + ", ".join(s["missing_states"]) + " (E10 3절)")
        if rules:
            L += ["", "**처리 규칙**", ""] + [f"- {r}" for r in rules]
    return "\n".join(L) + "\n"


def latest_sb_html() -> str:
    """05.outputs/의 가장 최근 sb-lowfi 결과 HTML (.edpm/ 기준 상대 경로)."""
    out = ROOT / "05.outputs"
    c = sorted([p for p in out.rglob("*.html") if "lowfi" in p.name], key=lambda p: p.stat().st_mtime) if out.exists() else []
    return os.path.relpath(c[-1], ROOT / ".edpm") if c else ""


def _editor_url() -> str:
    try:
        import edpm_dashboard as dash
        return dash.EDITOR
    except Exception:
        return os.environ.get("EDPM_EDITOR_URL", "antigravity-ide://file")


def write(quiet: bool = False) -> Path:
    data = build()
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "/*__EDPM_SCREENS__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    if not quiet:
        print(f"화면 지도: {OUT} (화면 {data['summary'].get('screens', 0)}개)" if data["e10"] else
              f"화면 지도: {OUT} — E10이 아직 없습니다 (/edpm-doc E10)")
    return OUT


def _git_rev() -> str:
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def archive(release: str, base: str = "", capture: bool = False) -> tuple[Path, list[dict]]:
    """릴리스 화면 아카이브. 화면의 기준은 배포된 코드이고, 아카이브는 릴리스마다 그 모습을 남기는 기록이다.
    E10 8절 '주소'가 있는 화면만 자동 캡처 대상이며, 결과는 index.md 한 장으로 본다."""
    data = build()
    day = dt.date.today().strftime("%Y%m%d")
    out = ROOT / "05.outputs" / "화면아카이브" / f"{release}_{day}"
    out.mkdir(parents=True, exist_ok=True)
    items = []
    for s in data["screens"]:
        sid = s["id"]
        url = (base.rstrip("/") + s["url"]) if (base and s["url"].startswith("/")) else s["url"]
        items.append({"id": sid, "name": s["name"], "url": url, "file": f"{sid}.png"})
    if capture:
        try:
            from playwright.sync_api import sync_playwright  # 선택 의존성
            with sync_playwright() as pw:
                b = pw.chromium.launch()
                pg = b.new_page(viewport={"width": 1280, "height": 900})
                for it in items:
                    if it["url"].startswith("http"):
                        try:
                            pg.goto(it["url"], wait_until="networkidle", timeout=20000)
                            pg.screenshot(path=str(out / it["file"]), full_page=True)
                        except Exception as e:  # 한 화면 실패가 전체를 막지 않게
                            it["error"] = str(e)[:120]
                b.close()
        except ImportError:
            print("Playwright가 없어 직접 캡처하지 않았습니다. webapp-testing 스킬이나 브라우저 도구로 아래 경로에 저장한 뒤 다시 실행하면 index가 갱신됩니다.")
    rows = []
    for it in items:
        have = (out / it["file"]).exists()
        st = "캡처됨" if have else ("실패: " + it["error"] if it.get("error") else ("캡처 대기" if it["url"] else "주소 없음 (E10 8절 `- 주소:`)"))
        it["status"] = st
        img = f"![{it['id']}]({it['file']})" if have else "-"
        rows.append(f"| {it['id']} | {it['name']} | {it['url'] or '-'} | {st} | {img} |")
    e10 = data["e10"] or {}
    head = [f"# 화면 아카이브 {release} ({dt.date.today()})", "",
            f"- 기준: 배포된 화면 (base {base or '-'}), 커밋 {_git_rev() or '-'}, E10 {e10.get('status', '-')}",
            "- 화면의 기준은 배포된 코드입니다. 이 폴더는 릴리스마다 그 모습을 남기는 기록이며 고치지 않습니다.",
            "- Figma에도 남기려면 `/edpm-change archive`의 Figma 단계(버전별 페이지)를 따릅니다.", "",
            "| SCR | 화면 | 주소 | 상태 | 캡처 |", "|-----|------|------|------|------|"]
    (out / "index.md").write_text("\n".join(head + rows) + "\n", encoding="utf-8")
    return out, items


def main() -> int:
    if "--archive" in sys.argv:
        i = sys.argv.index("--archive")
        rel = sys.argv[i + 1] if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith("--") else ""
        if not rel:
            print("사용: edpm_screens.py --archive <릴리스> [--base <URL>] [--capture]"); return 1
        base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else ""
        if not build()["e10"]:
            print("E10이 아직 없습니다 (/edpm-doc E10)."); return 1
        out, items = archive(rel, base, "--capture" in sys.argv)
        n = sum(1 for x in items if x["status"] == "캡처됨")
        print(f"화면 아카이브: {out.relative_to(ROOT)}/index.md — 화면 {len(items)}개, 캡처됨 {n}, "
              f"주소 없음 {sum(1 for x in items if x['status'].startswith('주소 없음'))}")
        if "--json" in sys.argv:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    if "--sb-md" in sys.argv:
        i = sys.argv.index("--sb-md")
        dest = Path(sys.argv[i + 1]) if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith("--") else ROOT / "05.outputs" / "화면설계서.md"
        data = build()
        if not data["e10"]:
            print("E10이 아직 없습니다 (/edpm-doc E10)."); return 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(to_sb_md(data), encoding="utf-8")
        print(f"sb-lowfi 입력: {dest} (화면 {len(data['screens'])}개) — 다음: sb-lowfi-pptx 스킬로 HTML·PPTX, sb-lowfi-figma로 Figma")
        return 0
    if "--json" in sys.argv:
        print(json.dumps(build(), ensure_ascii=False, indent=2))
        return 0
    write("--quiet" in sys.argv)
    if "--open" in sys.argv and sys.platform == "darwin":
        subprocess.run(["open", str(OUT)], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
