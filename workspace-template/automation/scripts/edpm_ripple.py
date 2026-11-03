#!/usr/bin/env python3
"""EdPM 변경 전파: 하나를 고치면 연결된 곳(하위 산출물, 같은 ID를 쓰는 문서, 테스트·코드, WBS, 화면)을 찾아
함께 고치게 한다. LLM 없이 frontmatter의 requires와 문서 속 ID(REQ·F·SCR·US·AC·T …)만으로 판정한다.

사용:
  python3 automation/scripts/edpm_ripple.py <문서 경로|ID> [--json]   # 이 문서가 바뀌면 닿는 곳
  python3 automation/scripts/edpm_ripple.py pending [--json]           # 전파 대기 목록 (상황판·대시보드에 표시)
  python3 automation/scripts/edpm_ripple.py ack <대상 경로|ID> <사유>   # 확인했고 고칠 것 없음 → 대기에서 뺌
  python3 automation/scripts/edpm_ripple.py wbs [<원천 경로|ID>] [--write]  # 전파 대기를 WBS 작업 후보로 (--write면 M02_WBS.csv에 추가)
  python3 automation/scripts/edpm_ripple.py record                     # PostToolUse 훅 (stdin JSON): 본문이 바뀌었으면 전파 대기 기록
  python3 automation/scripts/edpm_ripple.py snapshot                   # SessionStart 훅: 아직 지문이 없는 문서의 본문 지문 기록

동작:
- 산출물 본문(frontmatter 제외)이 바뀌면, 그 문서를 전제(requires)로 쓰는 바로 아래 문서와 그 문서가 정의한 ID를
  쓰는 문서를 "전파 대기"로 기록한다 (n/a 제외). 상태(status)만 바꾼 저장은 변경으로 보지 않는다.
- 대기 중인 문서의 본문을 고치면 그 문서의 대기는 풀리고, 이번에는 그 문서의 하위로 전파된다 (한 단계씩 이어짐).
- 고칠 것이 없으면 ack로 사유와 함께 뺀다. 원장은 .edpm/ripple.json.
표준 라이브러리만 쓴다.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edpm_check as ck  # noqa: E402

ROOT = ck.ROOT
LEDGER = ROOT / ".edpm" / "ripple.json"
WBS = ck.DOCS / "M.관리" / "M02_WBS.csv"
TODAY = dt.date.today()

# 전역 ID: 워크스페이스 어디서 써도 같은 것을 가리킴. 지역 ID(US·T·AC·IF)는 문서·과제 폴더마다 다시 매기므로 같은 폴더만.
GLOBAL_ID = re.compile(r"\b(?:REQ-\d+|F-\d{3}|SCR-\d{2,4}|LO-\d+|EV-[A-Z]*\d+|M-[A-Z]*\d+|LA-\d+|FI-\d+|EX-\d+|PB-\d+|IN-\d+|GR-\d+)\b")
LOCAL_ID = re.compile(r"\b(?:US-\d+|T-\d+|AC-\d+|IF-\d+)\b")
TEXT_SUFFIX = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".sql", ".html", ".css", ".vue", ".svelte", ".yml", ".yaml"}
STAGE = {"1.발견": "발견", "2.정의": "정의", "3.설계": "설계", "4.구축": "구축", "5.검증": "검증", "6.출시": "출시", "7.측정": "측정"}


# ---------- 원장 ----------

def load() -> dict:
    try:
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("bodies", {}); data.setdefault("pending", []); data.setdefault("history", [])
    return data


def save(data: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    data["history"] = data["history"][-200:]
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def body(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            return text[end + 4:].strip()
    return text.strip()


def digest(text: str) -> str:
    return hashlib.sha1(body(text).encode("utf-8")).hexdigest()


def _git_head(rel: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{rel}"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


# ---------- ID ----------

def _real(line: str) -> bool:
    return "예시" not in line and "{" not in line


def _lines(text: str):
    """예시·플레이스홀더가 아닌 줄. 제목에 '예시'가 있는 절(### F-012 (예시) 등) 안의 줄도 뺀다."""
    skip_level = 0
    for ln in body(text).splitlines():
        s = ln.strip()
        if s.startswith("#"):
            level = len(s) - len(s.lstrip("#"))
            if skip_level and level <= skip_level:
                skip_level = 0
            if "예시" in s:
                skip_level = level
                continue
        if skip_level or not _real(s):
            continue
        yield s


def owned_ids(text: str) -> set[str]:
    """이 문서가 정의하는 ID: 표의 첫 열, 제목의 ID."""
    out = set()
    for s in _lines(text):
        first = s.strip("|").split("|")[0] if s.startswith("|") else s.lstrip("#") if s.startswith("#") else ""
        out |= set(GLOBAL_ID.findall(first)) | set(LOCAL_ID.findall(first))
    return out


def mentioned_ids(text: str) -> set[str]:
    out = set()
    for s in _lines(text):
        out |= set(GLOBAL_ID.findall(s)) | set(LOCAL_ID.findall(s))
    return out


# ---------- 전파 범위 ----------

_TEMPLATES: dict[str, set[str]] = {}


def written(d: dict) -> bool:
    """내용을 쓴 문서인가: review·done, 또는 draft인데 updated 날짜가 적혔거나 본문이 보관함 템플릿과 다름.
    손대지 않은 템플릿(updated: YYYY-MM-DD 그대로)은 전파 대상이 아니다."""
    if d["status"] in {"review", "done"}:
        return True
    if d["status"] == "n/a":
        return False
    if ck.parse_date(d["fm"].get("updated")):
        return True
    name = d["path"].name
    if name not in _TEMPLATES:
        _TEMPLATES[name] = {digest(ck.read(x)) for x in ck.LIB.rglob(name)} if ck.LIB.exists() else set()
    return bool(_TEMPLATES[name]) and digest(ck.read(d["path"])) not in _TEMPLATES[name]


def resolve(arg: str, docs: list[dict]) -> dict | None:
    p = Path(arg)
    cand = (p if p.is_absolute() else (Path.cwd() / p)).resolve()
    for d in docs:
        if d["path"].resolve() == cand or d["rel"] == arg:
            return d
    return ck.find(docs, arg)


def children(src: dict, docs: list[dict]) -> list[dict]:
    """src를 전제(requires)로 쓰는 바로 아래 문서. 과제·프로토타입 폴더 안에서는 같은 폴더의 것을 가리킨다."""
    out = []
    for d in docs:
        if d is src:
            continue
        for req in d["fm"].get("requires", []) or []:
            rid = req.split("(")[0].strip()
            if rid != src["id"]:
                continue
            target = ck.find(docs, rid, d["folder"])
            if target is not None and target["path"] == src["path"]:
                out.append(d); break
    return out


def downstream(src: dict, docs: list[dict]) -> list[tuple[dict, int]]:
    seen, out, frontier = {src["rel"]}, [], [src]
    depth = 0
    while frontier and depth < 6:
        depth += 1
        nxt = []
        for f in frontier:
            for c in children(f, docs):
                if c["rel"] not in seen:
                    seen.add(c["rel"]); out.append((c, depth)); nxt.append(c)
        frontier = nxt
    return out


def related(src: dict, docs: list[dict], ids: set[str]) -> list[tuple[dict, list[str]]]:
    out = []
    g = {i for i in ids if GLOBAL_ID.fullmatch(i)}
    loc = ids - g
    for d in docs:
        if d is src:
            continue
        m = mentioned_ids(ck.read(d["path"]))
        hit = sorted(g & m) + (sorted(loc & m) if d["folder"] == src["folder"] else [])
        if hit:
            out.append((d, hit))
    return out


def files_using(ids: set[str], top: str) -> list[tuple[str, list[str]]]:
    base = ROOT / top
    if not base.exists() or not ids:
        return []
    out = []
    for p in sorted(base.rglob("*")):
        if not p.is_file() or p.suffix not in TEXT_SUFFIX or "node_modules" in p.parts or p.stat().st_size > 400_000:
            continue
        found = sorted(i for i in ids if re.search(rf"(?<![\w-]){re.escape(i)}(?![\w])", ck.read(p)))
        if found:
            out.append((str(p.relative_to(ROOT)), found))
    return out


def wbs_rows() -> list[dict]:
    return [r for r in ck.read_csv(WBS) if r.get("wp_id")]


def wbs_hits(doc_ids: set[str], ids: set[str]) -> list[dict]:
    out = []
    for r in wbs_rows():
        outs = {x.strip() for x in re.split(r"[;,\s]+", r.get("산출물ID") or "") if x.strip()}
        name_ids = set(GLOBAL_ID.findall(r.get("이름") or "")) | set(LOCAL_ID.findall(r.get("이름") or ""))
        if outs & doc_ids or name_ids & ids:
            act = "완료된 작업 — 다시 할 일이 생기면 변경 작업을 새로 추가" if r.get("상태") == "완료" else "일정 영향 확인 (/edpm-wbs impact)"
            out.append({**r, "할 일": act})
    return out


def ripple(src: dict, docs: list[dict]) -> dict:
    text = ck.read(src["path"])
    ids = owned_ids(text)
    down = downstream(src, docs)
    down_rel = {d["rel"] for d, _ in down}
    rel = [(d, hit) for d, hit in related(src, docs, ids) if d["rel"] not in down_rel]
    # 테스트·코드는 전역 ID와 작업 ID(T-07, 테스트 이름에 씀)로만 찾는다. AC-1·US-01은 문서마다 다시 매겨 오탐이 많다
    code_ids = {i for i in ids if GLOBAL_ID.fullmatch(i) or i.startswith("T-")}
    doc_ids = {src["id"]} | {d["id"] for d, _ in down} | {d["id"] for d, _ in rel}
    screens = []
    scr = sorted(i for i in ids if i.startswith("SCR-"))
    if src["id"] == "E10" or scr:
        screens = ["화면 지도(.edpm/screens.html)는 저장 훅이 다시 만듭니다",
                   "sb-lowfi 화면설계서를 쓰고 있으면 `edpm_screens.py --sb-md`로 입력 md를 다시 만들고 sb-lowfi-pptx로 다시 그립니다",
                   "이미 출시된 화면이면 다음 릴리스 아카이브에 반영됩니다 (/edpm-change archive)"]
    return {
        "source": {"id": src["id"], "rel": src["rel"], "status": src["status"]},
        "ids": sorted(ids),
        "downstream": [{"id": d["id"], "rel": d["rel"], "status": d["status"], "depth": n} for d, n in down if written(d)],
        "related": [{"id": d["id"], "rel": d["rel"], "status": d["status"], "ids": hit} for d, hit in rel if written(d)],
        "tests": [{"path": p, "ids": i} for p, i in files_using(code_ids, "tests")],
        "code": [{"path": p, "ids": i} for p, i in files_using(code_ids, "src")],
        "wbs": [{"wp_id": r["wp_id"], "이름": r.get("이름", ""), "상태": r.get("상태", ""), "할 일": r["할 일"]} for r in wbs_hits(doc_ids, ids)],
        "screens": screens,
    }


def fmt(r: dict) -> str:
    s = r["source"]
    L = [f"# 변경 전파: {s['id']} ({s['rel']}, {s['status']})"]
    L.append(f"이 문서가 정의하는 ID {len(r['ids'])}개: " + (", ".join(r["ids"][:30]) + (" …" if len(r["ids"]) > 30 else "") if r["ids"] else "없음"))
    L.append("\n## 1. 하위 산출물 (이 문서를 전제로 씀, 아직 손대지 않은 템플릿은 제외)")
    L += [f"- {'  ' * (x['depth'] - 1)}{x['id']} {x['rel']} ({x['status']})" + (" — 바로 아래" if x["depth"] == 1 else "") for x in r["downstream"]] or ["- 없음"]
    L.append("\n## 2. 같은 ID를 쓰는 문서")
    L += [f"- {x['id']} {x['rel']} ({x['status']}): {', '.join(x['ids'][:8])}" for x in r["related"]] or ["- 없음"]
    L.append("\n## 3. 테스트·코드")
    L += [f"- {x['path']}: {', '.join(x['ids'][:8])} — 인수조건이 바뀌면 스펙 승인 후 `.edpm/test-unlock`에 경로·사유를 적고 고칩니다" for x in r["tests"]]
    L += [f"- {x['path']}: {', '.join(x['ids'][:8])}" for x in r["code"]]
    if not r["tests"] and not r["code"]:
        L.append("- 없음")
    L.append("\n## 4. WBS")
    L += [f"- {x['wp_id']} {x['이름']} ({x['상태'] or '-'}): {x['할 일']}" for x in r["wbs"]] or ["- 연결된 작업 없음"]
    L.append("- 전파 작업을 WBS에 넣으려면: `edpm_ripple.py wbs " + s["id"] + "` (확인 후 `--write`)")
    if r["screens"]:
        L.append("\n## 5. 화면")
        L += [f"- {x}" for x in r["screens"]]
    L.append("\n순서: 바로 아래 문서부터 고칩니다. 고치면 그 문서의 하위로 다시 전파됩니다. 고칠 것이 없으면 `edpm_ripple.py ack <문서> <사유>`.")
    return "\n".join(L)


# ---------- 대기 ----------

def add_pending(data: dict, src: dict, docs: list[dict]) -> list[dict]:
    """src 본문이 바뀌었을 때: 바로 아래 문서 + 같은 ID를 쓰는 문서를 대기에 추가."""
    ids = owned_ids(ck.read(src["path"]))
    targets = [(d, "전제로 씀") for d in children(src, docs)]
    known = {d["rel"] for d, _ in targets}
    targets += [(d, "같은 ID: " + ", ".join(hit[:5])) for d, hit in related(src, docs, ids) if d["rel"] not in known]
    added = []
    for d, why in targets:
        if not written(d) or d["rel"] == src["rel"]:
            continue
        if any(p["source"] == src["rel"] and p["target"] == d["rel"] for p in data["pending"]):
            continue
        e = {"source": src["rel"], "source_id": src["id"], "target": d["rel"], "target_id": d["id"],
             "why": why, "date": str(TODAY)}
        data["pending"].append(e); added.append(e)
    return added


def clear_target(data: dict, rel: str, how: str) -> int:
    keep, gone = [], []
    for p in data["pending"]:
        (gone if p["target"] == rel else keep).append(p)
    data["pending"] = keep
    for p in gone:
        data["history"].append({**p, "resolved": str(TODAY), "how": how})
    return len(gone)


def pending(data: dict | None = None) -> list[dict]:
    data = data or load()
    docs = {d["rel"]: d for d in ck.load_docs()}
    return [p for p in data["pending"] if p["target"] in docs and p["source"] in docs]


def record(stdin_text: str) -> str:
    try:
        inp = json.loads(stdin_text).get("tool_input", {}) or {}
    except ValueError:
        return ""
    fp = inp.get("file_path") or ""
    if not fp:
        return ""
    path = Path(fp) if Path(fp).is_absolute() else ROOT / fp
    try:
        rel = str(path.resolve().relative_to(ROOT))
    except ValueError:
        return ""
    if not (rel == "PRD.md" or (rel.startswith("03.docs/") and rel.endswith(".md"))):
        return ""  # 산출물이 아닌 저장(코드·위키·자료실)은 바로 통과
    docs = ck.load_docs()
    src = next((d for d in docs if d["rel"] == rel), None)
    if src is None:
        return ""
    data = load()
    text = ck.read(src["path"])
    new = digest(text)
    old = data["bodies"].get(rel)
    if old is None:
        head = _git_head(rel)
        old = digest(head) if head is not None else new
    data["bodies"][rel] = new
    if old == new:
        save(data); return ""
    cleared = clear_target(data, rel, "본문 갱신")
    added = add_pending(data, src, docs)
    save(data)
    if not added:
        return f"변경 전파: {src['id']} 대기 {cleared}건 해소, 새로 닿는 곳 없음." if cleared else ""
    names = ", ".join(f"{e['target_id']}" for e in added[:8])
    return (f"변경 전파: {src['id']} 본문이 바뀌어 연결된 {len(added)}곳을 확인해야 합니다 ({names}). "
            f"사용자에게 알리고 `/edpm-change`로 하나씩 갱신하거나, 고칠 것이 없으면 사유와 함께 "
            f"`edpm_ripple.py ack <문서> <사유>`. 전체 범위(테스트·코드·WBS): `edpm_ripple.py {src['id']}`")


def snapshot() -> int:
    data = load()
    n = 0
    for d in ck.load_docs():
        if d["rel"] not in data["bodies"]:
            data["bodies"][d["rel"]] = digest(ck.read(d["path"])); n += 1
    save(data)
    return n


# ---------- WBS ----------

def wbs_candidates(data: dict, source: dict | None) -> list[dict]:
    rows = wbs_rows()
    nums = [int(m.group(1)) for r in rows if (m := re.fullmatch(r"WP-R\.(\d+)", r["wp_id"]))]
    n = max(nums, default=0)
    docs = {d["rel"]: d for d in ck.load_docs()}
    exists = {(r.get("산출물ID") or "", r.get("이름") or "") for r in rows}
    out = []
    for p in pending(data):
        if source is not None and p["source"] != source["rel"]:
            continue
        t = docs[p["target"]]
        stage = STAGE.get(Path(p["target"]).parts[1] if len(Path(p["target"]).parts) > 2 else "", "변경")
        name = f"[변경] {p['target_id']} 갱신 — {p['source_id']} 변경 반영 ({p['why']})"
        if (p["target_id"], name) in exists:
            continue
        n += 1
        out.append({"wp_id": f"WP-R.{n}", "이름": name, "단계": stage, "산출물ID": p["target_id"],
                    "담당": t["fm"].get("owner") or "PM", "공수(일)": "1", "시작": str(TODAY),
                    "종료": str(TODAY + dt.timedelta(days=2)), "선행": "", "학사제약": "", "상태": "예정", "이슈": ""})
    return out


def write_wbs(rows: list[dict]) -> str:
    if not WBS.exists():
        return "M02_WBS.csv가 없습니다 (/edpm-wbs create 또는 /edpm-doc M02)."
    with WBS.open(encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    with WBS.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        for r in rows:
            w.writerow(r)
    return f"M02_WBS.csv에 {len(rows)}행 추가. 일정 관리 도구에 올리려면 /edpm-wbs push (승인 후)."


# ---------- CLI ----------

def main() -> int:
    a = sys.argv[1:]
    if not a:
        print(__doc__); return 0
    if a[0] == "record":
        msg = record(sys.stdin.read())
        if msg:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}, ensure_ascii=False))
        return 0
    if a[0] == "snapshot":
        n = snapshot()
        if "--quiet" not in a:
            print(f"지문 기록 {n}건")
        return 0
    if a[0] == "pending":
        ps = pending()
        if "--json" in a:
            print(json.dumps(ps, ensure_ascii=False, indent=2)); return 0
        if not ps:
            print("전파 대기 없음"); return 0
        print(f"# 전파 대기 {len(ps)}건 (원천 → 확인할 문서)")
        for p in ps:
            print(f"- {p['source_id']} → {p['target_id']} {p['target']} — {p['why']} ({p['date']})")
        return 0
    docs = ck.load_docs()
    if a[0] == "ack":
        if len(a) < 3:
            print("사용: edpm_ripple.py ack <대상 경로|ID> <사유>"); return 1
        d = resolve(a[1], docs)
        if d is None:
            print(f"문서를 찾지 못함: {a[1]}"); return 1
        data = load()
        n = clear_target(data, d["rel"], "확인함: " + " ".join(a[2:]))
        save(data)
        print(f"{d['id']} 대기 {n}건 해소 — 사유: {' '.join(a[2:])}"); return 0
    if a[0] == "wbs":
        pos = [x for x in a[1:] if not x.startswith("--")]
        src = resolve(pos[0], docs) if pos else None
        rows = wbs_candidates(load(), src)
        if not rows:
            print("WBS에 넣을 전파 작업이 없습니다."); return 0
        if "--write" in a:
            print(write_wbs(rows)); return 0
        keys = ("wp_id", "이름", "단계", "산출물ID", "담당", "공수(일)", "시작", "종료", "상태")
        w = csv.writer(sys.stdout)
        w.writerow(keys)
        for r in rows:
            w.writerow([r[k] for k in keys])
        print("\n확인 후 `--write`로 M02_WBS.csv에 추가합니다.")
        return 0
    src = resolve(a[0], docs)
    if src is None:
        print(f"문서를 찾지 못함: {a[0]}"); return 1
    r = ripple(src, docs)
    print(json.dumps(r, ensure_ascii=False, indent=2) if "--json" in a else fmt(r))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 훅에서 오류가 나도 작업을 막지 않는다
        if len(sys.argv) > 1 and sys.argv[1] in {"record", "snapshot"}:
            sys.exit(0)
        raise
