#!/usr/bin/env python3
"""EdPM 대시보드: 워크스페이스 상태를 HTML 한 장으로 (.edpm/dashboard.html).

사용:
  python3 automation/scripts/edpm_dashboard.py            # 만들기
  python3 automation/scripts/edpm_dashboard.py --open     # 만들고 브라우저로 열기
  python3 automation/scripts/edpm_dashboard.py --quiet    # 훅용: 출력 없이 만들기

판정은 edpm_check.py와 같은 함수를 그대로 쓴다 (새 기준을 만들지 않음). 화면은 보기 전용이며,
문서 상태를 바꾸는 일은 Claude Code가 한다. 문서를 누르면 설치된 편집기에서 열린다
(Antigravity IDE → Cursor → VS Code → Antigravity 순서로 찾음). 직접 정하려면 환경변수 EDPM_EDITOR_URL
(예: antigravity-ide://file, cursor://file, vscode://file).
외부 라이브러리·네트워크 없이 동작한다.
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
OUT = ROOT / ".edpm" / "dashboard.html"
TEMPLATE = Path(__file__).resolve().parent / "dashboard_template.html"
APPS = [("Antigravity IDE.app", "antigravity-ide://file"), ("Cursor.app", "cursor://file"),
        ("Visual Studio Code.app", "vscode://file"), ("Antigravity.app", "antigravity://file")]


def _editor_url() -> str:
    """macOS에서 Antigravity IDE와 Antigravity(별도 앱)가 함께 있으면 antigravity://는 IDE가 아닌 앱으로 간다.
    그래서 IDE가 등록한 antigravity-ide://를 먼저 쓴다."""
    if os.environ.get("EDPM_EDITOR_URL"):
        return os.environ["EDPM_EDITOR_URL"].rstrip("/")
    for app, url in APPS:
        if any((Path(base) / app).exists() for base in ("/Applications", Path.home() / "Applications")):
            return url
    return "antigravity-ide://file"


EDITOR = _editor_url()
GROUPS = {"domain": "도메인 지식", "company": "회사", "learners": "학습자", "research": "리서치",
          "market": "시장", "decisions": "결정", "curriculum": "교육과정"}
LINK = re.compile(r"\[\[([^\]|#]+)")


def domain_theme(text: str, name: str) -> str:
    """도메인 지식 페이지를 주제 군집으로 (type·tags·이름 기준)."""
    typ = (re.search(r"^type:\s*(\S+)", text, re.M) or [None, ""])[1]
    tags = (re.search(r"^tags:\s*(.*)$", text, re.M) or [None, ""])[1] + " " + name
    if typ in ("regulation", "standard"):
        return "규제·표준"
    if re.search(r"\bAI\b|LLM|RAG|튜터|생성", tags):
        return "AI"
    if re.search(r"IA|화면|UX|UI|대시보드|플레이어", tags):
        return "IA·화면"
    if re.search(r"학습과학|인지|기억|동기|피드백|평가|측정|숙달|형성|교수|학습설계|교육과정|성취", tags):
        return "학습과학·평가"
    if typ == "metric" or re.search(r"지표|코호트|리텐션", tags):
        return "지표·데이터"
    return "비즈니스·운영"


def _open_url(p: Path) -> str:
    return f"{EDITOR}{p.resolve().as_posix()}"


def graph(docs: list[dict]) -> dict:
    nodes, edges, index = [], [], {}
    pages = []
    if ck.WIKI.exists():
        for p in sorted(ck.WIKI.rglob("*.md")):
            rel = p.relative_to(ck.WIKI)
            if p.name in {"index.md", "log.md"} or any(x.startswith("_") for x in rel.parts):
                continue
            key = rel.with_suffix("").as_posix()
            grp = rel.parts[0] if len(rel.parts) > 1 else "기타"
            label = domain_theme(ck.read(p), p.stem) if grp == "domain" else GROUPS.get(grp, "기타")
            index[key] = len(nodes)
            nodes.append({"id": key, "label": p.stem, "group": label, "url": _open_url(p),
                          "rel": f"02.wiki/{rel.as_posix()}"})
            pages.append((key, p))
    by_stem = {}
    for k in index:
        by_stem.setdefault(k.split("/")[-1], []).append(k)
    for d in docs:
        key = f"doc:{d['rel']}"
        index[key] = len(nodes)
        nodes.append({"id": key, "label": f"{d['id']} {d['fm'].get('title', '')}".strip(), "group": "산출물",
                      "status": d["status"], "url": _open_url(d["path"]), "rel": d["rel"]})

    def resolve(t: str):
        t = t.strip().removeprefix("02.wiki/").removesuffix(".md")
        if t in index:
            return index[t]
        c = by_stem.get(t.split("/")[-1], [])
        return index[c[0]] if len(c) == 1 else None

    seen = set()

    def add(a, b):
        if a is None or b is None or a == b or (a, b) in seen or (b, a) in seen:
            return
        seen.add((a, b))
        edges.append([a, b])

    for key, p in pages:
        for m in LINK.finditer(ck.read(p)):
            add(index[key], resolve(m.group(1)))
    doc_by_id = {}
    for d in docs:
        doc_by_id.setdefault(d["id"], index[f"doc:{d['rel']}"])
    for d in docs:
        me = index[f"doc:{d['rel']}"]
        for r in d["fm"].get("requires", []) or []:
            add(me, doc_by_id.get(r.split("(")[0].strip()))
        for m in LINK.finditer(ck.read(d["path"])):
            add(me, resolve(m.group(1)))
    deg = [0] * len(nodes)
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    for n, k in zip(nodes, deg):
        n["deg"] = k
    return {"nodes": nodes, "edges": edges}


def calendar() -> dict:
    rows = [r for r in ck.read_csv(ck.DOCS / "M.관리" / "M02_WBS.csv") if r.get("wp_id")]
    first = ck.TODAY.replace(day=1)
    nxt = (first + dt.timedelta(days=32)).replace(day=1)
    days = {}
    items = []
    for r in rows:
        s, e = ck.parse_date(r.get("시작")), ck.parse_date(r.get("종료"))
        if not s or not e:
            continue
        d = max(s, first)
        while d <= e and d < nxt:
            days[d.day] = days.get(d.day, 0) + 1
            d += dt.timedelta(days=1)
        if s <= ck.TODAY + dt.timedelta(days=14) and e >= ck.TODAY:
            items.append({"id": r["wp_id"], "name": r.get("이름", ""), "start": str(s), "end": str(e),
                          "status": r.get("상태", ""), "late": r.get("상태") != "완료" and e < ck.TODAY})
    return {"year": first.year, "month": first.month, "first_weekday": first.weekday(),
            "days_in_month": (nxt - first).days, "today": ck.TODAY.day, "load": days, "items": items[:6]}


# ---------- 여정 보드 ----------
STAGES = ["리서치", "PRD", "학습 성과", "요구사항", "스펙·설계", "구현·검증", "출시·효과"]


def stage_of(did: str) -> str | None:
    if did in {"E00", "PRD"}:
        return "PRD"
    if did in {"E01", "E02", "E03", "E04", "N01", "N02", "F00", "D01"}:
        return "리서치"
    if did in {"E05", "E07", "E08"}:
        return "학습 성과"
    if did in {"E06", "N03"}:
        return "요구사항"
    if did in {"E09", "E10", "E11", "E12", "E13", "E14", "S06", "S07"} or did[:1] in {"A", "L", "P"} or did in {"B01", "B02", "B03", "B04", "B05"}:
        return "스펙·설계"
    if did in {"B06", "B07", "E15", "E16"}:
        return "구현·검증"
    if did in {"E17", "E18", "E19", "E20", "N04"}:
        return "출시·효과"
    return None  # M·S·F·V는 아래 줄(lane)로


def current_stage(docs: list[dict], phase: dict) -> str:
    step = (phase.get("step") or "").split(" ")[0]
    st = {d["id"]: d["status"] for d in docs}
    if step in {"0", "1", "1.5"}:
        return "PRD"
    if step == "2":
        return "리서치"
    if step == "3":
        return "학습 성과" if st.get("E05") not in ("done", "n/a") else "요구사항"
    return {"4": "스펙·설계", "5": "구현·검증", "6": "출시·효과"}.get(step, "PRD")


def board(docs: list[dict], rows: list[dict], phase: dict) -> dict:
    state = {r["rel"]: r for r in rows}
    cols = {k: [] for k in STAGES}
    lanes = {"관리·보고": [], "사업": []}
    tasks = {}
    for d in sorted(docs, key=ck._order):
        r = state.get(d["rel"])
        card = {"id": d["id"], "title": d["fm"].get("title", ""), "status": d["status"],
                "state": r["state"] if r else ("해당없음" if d["status"] == "n/a" else ""),
                "updated": str(d["fm"].get("updated", "") or "").replace("YYYY-MM-DD", ""),
                "url": _open_url(d["path"]), "rel": d["rel"]}
        if d["id"] == "PRD":
            path = d["fm"].get("path") or []
            card["path"] = path if isinstance(path, list) else [path]
        sg = stage_of(d["id"])
        if sg:
            cols[sg].append(card)
        elif d["id"][:1] == "M":
            lanes["관리·보고"].append(card)
        elif d["id"][:1] == "S":
            lanes["사업"].append(card)
        elif d["id"] in {"F01", "F02", "F03", "F04"}:
            tasks.setdefault(d["folder"].name, []).append(card)
    feature = [{"name": k, "cards": sorted(v, key=lambda c: c["id"])} for k, v in sorted(tasks.items())]
    protos = []
    for pt in ck.read_csv(ck.DOCS / "V.프로토타입" / "프로토타입목록.csv"):
        end = ck.parse_date(pt.get("종료"))
        protos.append({"id": pt.get("PT", ""), "name": pt.get("이름", ""), "fidelity": pt.get("충실도", ""),
                       "status": pt.get("상태", ""), "decision": pt.get("결정", ""), "question": pt.get("검증질문", ""),
                       "dday": (end - ck.TODAY).days if end else None})
    return {"stages": STAGES, "current": current_stage(docs, phase), "cols": cols, "lanes": lanes,
            "feature": feature, "protos": protos}


# ---------- 스펙 추적 ----------

def _section_text(text: str, head: str) -> str:
    """head가 들어간 제목부터 다음 같은·상위 수준 제목 전까지의 본문."""
    out, on, level = [], False, 0
    for ln in text.splitlines():
        m = re.match(r"^(#+)\s", ln)
        if m:
            if on and len(m.group(1)) <= level:
                break
            if head in ln:
                on, level = True, len(m.group(1))
                continue
        if on:
            out.append(ln)
    return "\n".join(out)


def _ids(cell: str, prefix: str) -> list[str]:
    return re.findall(rf"{prefix}-[\w-]+", cell or "")


def trace(docs: list[dict]) -> dict:
    reqs = set()
    for d in docs:
        if d["id"] == "E06":
            for r in ck._rows(ck.read(d["path"]), "요구사항"):
                if r and re.match(r"REQ-\d+", r[0]) and ck._filled(r[1] if len(r) > 1 else ""):
                    reqs.add(r[0])
    out = []
    for d in docs:
        text = ck.read(d["path"])
        if d["id"] == "E09":
            feats = [r for r in ck._rows(text, "1. 기능 목록") if r and re.match(r"F-\d{3}$", r[0])]
            sec, cur = {}, None
            for ln in text.splitlines():
                if ln.startswith("## "):
                    cur = None
                m = re.match(r"^###\s+(F-\d{3})", ln)
                if m:
                    cur = None if ("예시" in ln or "{" in ln) else m.group(1)
                    if cur:
                        sec[cur] = {"us": 0, "ac": [], "state": False}
                    continue
                if cur:
                    t = ln.strip()
                    if t.startswith("| US-") and "{" not in t:
                        sec[cur]["us"] += 1
                    if re.match(r"\|\s*AC-\d+\s*\|", t) and "{" not in t:
                        sec[cur]["ac"].append(t.split("|")[1].strip())
                    if "stateDiagram" in t:
                        sec[cur]["state"] = True
            tasks = [r for r in ck._rows(text, "작업 분해") if r and re.match(r"T-\d+", r[0])]
            for f in feats:
                fid = f[0]
                info = sec.get(fid, {"us": 0, "ac": [], "state": False})
                ft = [t for t in tasks if len(t) > 2 and fid in t[2]]
                out.append(_trace_row(d, fid, f[1] if len(f) > 1 else "", _ids(f[3] if len(f) > 3 else "", "REQ"), reqs,
                                      info["us"], info["ac"], info["state"], ft, ac_col=3, test_col=4, status_col=-1))
        elif d["id"] == "F02" and "_과제템플릿" not in d["rel"]:
            n_us, acs = 0, []
            for ln in text.splitlines():
                t = ln.strip()
                if not t.startswith("| US-") or "(예시)" in t or "{" in t:
                    continue
                cells = [c.strip() for c in t.strip("|").split("|")]
                if len(cells) > 1 and cells[1].startswith("AC-"):
                    acs.append(cells[1])
                else:
                    n_us += 1
            sect = _section_text(text, "2.1 상태 흐름")
            tmpl = ck.LIB / "F.개선" / "_과제템플릿" / "F02_기능기획서.md"
            tsect = _section_text(ck.read(tmpl), "2.1 상태 흐름") if tmpl.exists() else ""
            has_state = "stateDiagram" in sect and sect.strip() != tsect.strip()
            tasks = [r for r in _table_with(text, "5.1", "T-ID") if re.match(r"T-\d+", r[0]) and "(예시)" not in " ".join(r)]
            out.append(_trace_row(d, d["folder"].name, d["fm"].get("title", "기능기획서"), [], None, n_us, acs, has_state,
                                  tasks, ac_col=2, test_col=3, status_col=-1))
    return {"rows": out, "req_known": bool(reqs),
            "summary": {"features": len(out), "broken": sum(1 for r in out if r["flags"])}}


def _table_with(text: str, head: str, first_col: str) -> list[list[str]]:
    """head가 들어간 제목 아래, 첫 열 머리글이 first_col인 표의 데이터 행."""
    on, found, rows = False, False, []
    for ln in text.splitlines():
        if ln.lstrip().startswith("#"):
            if found:
                break
            on = head in ln
            continue
        t = ln.strip()
        if not on or not t.startswith("|"):
            if found and rows and not t.startswith("|"):
                break
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        if not found:
            found = cells[0] == first_col
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows


def _trace_row(d, fid, name, req_ids, reqs, n_us, acs, has_state, tasks, ac_col, test_col, status_col):
    covered = set()
    no_test, test_missing = [], []
    for t in tasks:
        covered |= set(_ids(t[ac_col] if len(t) > ac_col else "", "AC"))
        tc = t[test_col] if len(t) > test_col else ""
        if not ck._filled(tc):
            no_test.append(t[0])
        elif tc.strip("`").startswith("tests/") and not (ROOT / tc.strip("` ").split()[0]).exists():
            test_missing.append(t[0])
    flags = []
    if reqs is not None and not req_ids:
        flags.append("REQ 연결 없음")
    elif reqs and any(r not in reqs for r in req_ids):
        flags.append("E06에 없는 REQ: " + ", ".join(r for r in req_ids if r not in reqs))
    if not n_us:
        flags.append("유저스토리 없음")
    if not acs:
        flags.append("인수조건 없음")
    left = [a for a in acs if a not in covered]
    if acs and left:
        flags.append("작업 없는 AC: " + ", ".join(left[:4]))
    if no_test:
        flags.append("테스트 없는 작업: " + ", ".join(no_test[:4]))
    if test_missing:
        flags.append("테스트 파일 없음: " + ", ".join(test_missing[:4]))
    done = sum(1 for t in tasks if (t[status_col] if t else "") == "완료")
    return {"doc": d["id"], "id": fid, "name": name, "req": req_ids, "us": n_us, "ac": len(acs), "state": bool(has_state),
            "tasks": len(tasks), "tasks_done": done, "tests": len(tasks) - len(no_test), "flags": flags,
            "url": _open_url(d["path"]), "rel": d["rel"]}


def recent_files(n: int = 8) -> list[dict]:
    cands = []
    for base in (ck.DOCS, ck.WIKI, ck.OPS, ROOT / "06.prototypes", ROOT / "05.outputs"):
        if base.exists():
            cands += [p for p in base.rglob("*") if p.is_file() and p.suffix in {".md", ".html", ".csv"}
                      and not any(x.startswith("_") for x in p.relative_to(ROOT).parts) and p.name != ".gitkeep"]
    prd = ROOT / "PRD.md"
    if prd.exists():
        cands.append(prd)
    cands.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": p.name, "rel": str(p.relative_to(ROOT)), "url": _open_url(p),
             "when": dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%m-%d %H:%M")} for p in cands[:n]]


def log_entries(n: int = 8) -> list[dict]:
    p = ck.WIKI / "log.md"
    if not p.exists():
        return []
    out = []
    for ln in ck.read(p).splitlines():
        m = re.match(r"^## \[(\d{4}-\d{2}-\d{2})\]\s*([^|]+)\|\s*(.+)$", ln)
        if m:
            out.append({"date": m.group(1), "action": m.group(2).strip(), "target": m.group(3).strip()})
    return out[-n:][::-1]


def skills() -> list[dict]:
    out = []
    for p in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        s = ck.read(p)
        name = re.search(r"^name:\s*(.+)$", s, re.M)
        desc = re.search(r"^description:\s*(.+)$", s, re.M)
        hint = re.search(r'^argument-hint:\s*"?(.*?)"?$', s, re.M)
        d = desc.group(1) if desc else ""
        out.append({"name": name.group(1).strip() if name else p.parent.name,
                    "desc": re.split(r"(?<=다)\. ", d)[0][:110], "hint": (hint.group(1) if hint else "")[:120]})
    return out


def build() -> dict:
    docs = ck.load_docs()
    r = ck.collect()
    prd = ck.find(docs, "PRD")
    clar = ck.clarity("PRD", ck.read(prd["path"]), docs) if prd else {}
    rows = ck.progress_rows(docs)
    for row in rows:
        d = next((x for x in docs if x["rel"] == row["rel"]), None)
        row["url"] = _open_url(d["path"]) if d else ""
    pf = ck.portfolio(docs)
    g = graph(docs)
    raw = len([p for p in ck.RAW.rglob("*") if p.is_file() and p.name not in {".gitkeep", "README.md", "_자료목록.md"}]) if ck.RAW.exists() else 0
    attention = []
    d = r["docs"]
    for x in d["blocked_done"][:3]:
        attention.append({"kind": "게이트", "text": x})
    for x in r["decisions_due"][:3]:
        attention.append({"kind": "결정 재검토", "text": f"{x['id']} {x['title']} (재검토일 {x['review']}) → /edpm-decide review"})
    for x in r["meetings_pending"][:3]:
        attention.append({"kind": "회의록", "text": f"위키 반영 안 됨: {x} → /edpm-brief meeting ingest"})
    for x in r["wbs"]["overdue"][:3]:
        attention.append({"kind": "지연", "text": f"{x['wp_id']} {x.get('이름', '')} (종료 {x.get('종료')})"})
    for x in r["proto"]["undecided"][:3]:
        attention.append({"kind": "프로토타입", "text": f"{x['PT']} {x.get('이름', '')} 결정 안 함 → /edpm-proto decide"})
    for x in r.get("unknowns_pending", [])[:3]:
        attention.append({"kind": "아직 모르는 것", "text": x})
    for x in d["review"][:3]:
        attention.append({"kind": "검토 대기", "text": x})
    for x in d["gate_skip"][:3]:
        attention.append({"kind": "게이트 스킵", "text": x})
    if r["pii"]:
        attention.append({"kind": "개인정보", "text": f"식별 정보 의심 {len(r['pii'])}곳 → /edpm-wiki lint pii"})
    for x in r.get("test_unlocks", [])[:2]:
        attention.append({"kind": "테스트 해제", "text": x})
    return {
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "today": str(ck.TODAY), "context": r["context"], "phase": r["phase"],
        "clarity": clar, "progress": rows, "outside": ck.outside_path(docs),
        "counts": {"wiki": sum(1 for n in g["nodes"] if n["group"] != "산출물"), "docs": len(docs),
                   "decisions": len(pf["decisions"]), "raw": raw, "library": len([x for x in ck.library_docs() if x["id"] not in {y['id'] for y in docs}])},
        "by_status": d["by_status"], "open_marks": pf["open_marks"], "decision_score": pf["decision_score"],
        "decisions": pf["decisions"][-6:], "prototypes": pf["prototypes"], "spec": pf["spec"],
        "attention": attention, "calendar": calendar(), "recent": recent_files(), "log": log_entries(),
        "skills": skills(), "graph": g, "board": board(docs, ck.progress_rows(docs, show_all=True), r["phase"]),
        "trace": trace(docs),
    }


def main() -> int:
    data = build()
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "/*__EDPM_DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    if "--quiet" not in sys.argv:
        print(f"대시보드: {OUT}")
    if "--open" in sys.argv and sys.platform == "darwin":
        subprocess.run(["open", str(OUT)], check=False)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 훅에서 불릴 때 작업을 막지 않는다
        if "--quiet" not in sys.argv:
            raise
        print(f"대시보드 생성 오류 (무시): {e}", file=sys.stderr)
        sys.exit(0)
