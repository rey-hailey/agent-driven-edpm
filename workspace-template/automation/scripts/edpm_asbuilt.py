#!/usr/bin/env python3
"""EdPM 현행화(as-built): 출시한 코드와 문서를 대조해 차이를 남긴다. 출시 전에는 스펙이 기준이고, 출시 후에는
배포된 코드가 기준이며 문서가 따라간다. 차이를 찾는 것은 이 스크립트가, 판정(문서 갱신 / 결함 / 의도된 차이)은 PM이 한다.

사용:
  python3 automation/scripts/edpm_asbuilt.py scan [--code <경로>] [--json]       # 대조만 (기록하지 않음)
  python3 automation/scripts/edpm_asbuilt.py record <릴리스> [--code <경로>]      # 05.outputs/현행화/<릴리스>_<날짜>.md
  python3 automation/scripts/edpm_asbuilt.py record <릴리스> --no-code "<사유>"   # 코드를 볼 수 없을 때 (화면은 /edpm-change screen으로)
  python3 automation/scripts/edpm_asbuilt.py status [--json]                     # 기록 목록과 판정 안 된 행

대조하는 것:
  화면  코드의 화면 경로 (Next.js app/·pages/)        ↔ E10 8절 `- 주소:`
  API   코드의 API 경로·메서드 (Next.js route·pages/api, Express·FastAPI 라우터) ↔ B02 2절 API 목록
  기능  코드 주석·이름에 쓴 기능 ID(F-001)           ↔ E09 1절 기능 목록·F02 (후속 릴리스 제외)
코드 경로: --code, 없으면 AGENTS.md 2절 '제품 코드 위치', 없으면 src/. 코드는 읽기만 한다. 표준 라이브러리만 쓴다.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edpm_check as ck  # noqa: E402

ROOT = ck.ROOT
OUT = ROOT / "05.outputs" / "현행화"
SKIP_DIRS = {"node_modules", ".next", "dist", "build", ".git", "__pycache__", ".venv", "coverage", ".turbo", ".vercel"}
CODE_SUFFIX = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".vue", ".svelte", ".mdx"}
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
PENDING = "{판정}"


# ---------- 코드 ----------

def code_root(arg: str = "") -> Path | None:
    if arg:
        p = Path(arg).expanduser()
        return (p if p.is_absolute() else ROOT / p).resolve()
    m = re.search(r"^\| 제품 코드 위치 \| (.+?) \|", ck.read(ROOT / "AGENTS.md"), re.M)
    if m and not m.group(1).startswith("{"):
        v = m.group(1).split("—")[0].strip().strip("`")
        p = Path(v).expanduser()
        p = p if p.is_absolute() else ROOT / p
        if p.exists():
            return p.resolve()
    return (ROOT / "src").resolve() if (ROOT / "src").exists() else None


def _files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in CODE_SUFFIX and not (set(p.relative_to(root).parts) & SKIP_DIRS) and p.stat().st_size < 400_000:
            yield p


def _seg(s: str) -> str:
    """경로 조각을 비교용으로: [id]·[...slug]·{id}·:id → :p"""
    return ":p" if re.fullmatch(r"\[.*\]|\{.*\}|:.+", s) else s.lower()


def norm(path: str) -> str:
    path = re.sub(r"^https?://[^/]+", "", path.strip().strip("`")).split("?")[0].split("#")[0]
    parts = [_seg(x) for x in path.split("/") if x]
    return "/" + "/".join(parts)


def same(a: str, b: str) -> bool:
    x, y = norm(a).split("/"), norm(b).split("/")
    return len(x) == len(y) and all(p == q or ":p" in (p, q) for p, q in zip(x, y))


def _next_route(rel_parts: tuple[str, ...]) -> str:
    keep = [p for p in rel_parts if not (p.startswith("(") and p.endswith(")")) and not p.startswith("@")]
    return "/" + "/".join(keep)


def scan_code(root: Path) -> dict:
    screens, apis, fids = [], [], {}
    for p in _files(root):
        rel = p.relative_to(root)
        parts = rel.parts
        text = ck.read(p)
        for f in set(re.findall(r"\bF-\d{3}\b", text)):
            fids.setdefault(f, []).append(str(rel))
        if "app" in parts[:-1]:
            i = parts.index("app")
            inner = parts[i + 1:-1]
            stem = p.stem
            if stem == "page":
                screens.append({"path": _next_route(inner), "file": str(rel)})
                continue
            if stem == "route":
                ms = sorted(set(re.findall(r"export\s+(?:async\s+)?(?:function|const)\s+(GET|POST|PUT|PATCH|DELETE)\b", text))) or ["*"]
                apis.append({"path": _next_route(inner), "methods": ms, "file": str(rel)})
                continue
        if "pages" in parts[:-1]:
            i = parts.index("pages")
            inner = list(parts[i + 1:-1]) + ([] if p.stem == "index" else [p.stem])
            if p.stem.startswith("_"):
                continue
            if inner[:1] == ["api"]:
                apis.append({"path": "/" + "/".join(inner), "methods": ["*"], "file": str(rel)})
            else:
                screens.append({"path": "/" + "/".join(inner), "file": str(rel)})
            continue
        for m in re.finditer(r"\b(?:app|router)\.(get|post|put|patch|delete)\(\s*['\"`]([^'\"`]+)", text):
            apis.append({"path": m.group(2), "methods": [m.group(1).upper()], "file": str(rel), "note": "라우터 접두사 확인"})
        for m in re.finditer(r"@(?:app|router)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)", text):
            apis.append({"path": m.group(2), "methods": [m.group(1).upper()], "file": str(rel), "note": "라우터 접두사 확인"})
    merged: dict[str, dict] = {}
    for a in apis:  # 같은 경로는 합침
        k = norm(a["path"])
        if k in merged:
            merged[k]["methods"] = sorted(set(merged[k]["methods"]) | set(a["methods"]))
        else:
            merged[k] = dict(a)
    return {"screens": screens, "apis": list(merged.values()), "feature_ids": fids}


# ---------- 문서 ----------

def doc_screens(docs: list[dict]) -> list[dict]:
    try:
        import edpm_screens as sc
        data = sc.build()
    except Exception:
        return []
    return [{"id": s["id"], "name": s["name"], "path": s.get("url", "")} for s in data.get("screens", [])]


def doc_apis(docs: list[dict]) -> list[dict]:
    b02 = ck.find(docs, "B02")
    if b02 is None or b02["status"] == "n/a":
        return []
    out = []
    for r in ck._table_rows(ck.read(b02["path"]), "2. API 목록"):
        if not r or "예시" in " ".join(r) or "{" in r[0] or len(r) < 2:
            continue
        m = re.match(r"\s*([A-Z]+)\s+(\S+)", r[1])
        if m:
            out.append({"id": r[0], "methods": [m.group(1)], "path": m.group(2)})
    return out


def doc_features(docs: list[dict]) -> dict[str, str]:
    """기능 ID → 상태 (E09 1절, F02 제목·스토리에 쓴 F-ID)."""
    out = {}
    e09 = ck.find(docs, "E09")
    if e09 is not None:
        for r in ck._table_rows(ck.read(e09["path"]), "1. 기능 목록"):
            if r and re.fullmatch(r"F-\d{3}", r[0]):
                out[r[0]] = r[-1]
    for d in docs:
        if d["id"] == "F02" and "_과제템플릿" not in d["rel"]:
            for f in re.findall(r"\bF-\d{3}\b", ck.read(d["path"])):
                out.setdefault(f, "F02")
    return out


# ---------- 대조 ----------

def compare(code: dict | None, docs: list[dict]) -> dict:
    rows, matched = [], []
    ds, da, df = doc_screens(docs), doc_apis(docs), doc_features(docs)
    if code is None:
        return {"rows": rows, "matched": matched, "counts": {}, "docs": {"screens": len(ds), "apis": len(da), "features": len(df)}}
    # 화면
    with_path = [s for s in ds if s["path"]]
    for c in code["screens"]:
        hit = next((s for s in with_path if same(s["path"], c["path"])), None)
        if hit:
            matched.append(f"화면 {hit['id']} {c['path']}")
        else:
            rows.append({"kind": "화면", "item": c["path"], "code": c["file"], "doc": "-", "diff": "코드에만 (E10에 없음)"})
    for s in with_path:
        if not any(same(s["path"], c["path"]) for c in code["screens"]) and code["screens"]:
            rows.append({"kind": "화면", "item": f"{s['id']} {s['name']}", "code": "-", "doc": f"E10 주소 {s['path']}", "diff": "문서에만 (코드에 없음)"})
    if code["screens"]:
        for s in ds:
            if not s["path"]:
                rows.append({"kind": "화면", "item": f"{s['id']} {s['name']}", "code": "?", "doc": "E10 (주소 없음)", "diff": "주소 없음 — 대조 불가"})
    # API
    for c in code["apis"]:
        hit = next((a for a in da if same(a["path"], c["path"])), None)
        if hit is None:
            rows.append({"kind": "API", "item": f"{'·'.join(c['methods'])} {c['path']}", "code": c["file"] + (f" ({c['note']})" if c.get("note") else ""),
                         "doc": "-", "diff": "코드에만 (B02에 없음)"})
        elif "*" not in c["methods"] and not set(hit["methods"]) <= set(c["methods"]):
            rows.append({"kind": "API", "item": f"{hit['id']} {c['path']}", "code": "·".join(c["methods"]), "doc": "·".join(hit["methods"]), "diff": "메서드 다름"})
        else:
            matched.append(f"API {hit['id']} {c['path']}")
    for a in da:
        if code["apis"] and not any(same(a["path"], c["path"]) for c in code["apis"]):
            rows.append({"kind": "API", "item": f"{a['id']} {'·'.join(a['methods'])} {a['path']}", "code": "-", "doc": "B02", "diff": "문서에만 (코드에 없음)"})
    # 기능 ID
    fids = code["feature_ids"]
    for f, files in sorted(fids.items()):
        st = df.get(f)
        if st is None:
            rows.append({"kind": "기능", "item": f, "code": ", ".join(files[:3]), "doc": "-", "diff": "코드에만 (E09·F02에 없음)"})
        elif "후속" in st:
            rows.append({"kind": "기능", "item": f, "code": ", ".join(files[:3]), "doc": "E09 후속 릴리스", "diff": "후속 릴리스인데 이미 구현됨"})
        else:
            matched.append(f"기능 {f}")
    if fids:  # 코드에 기능 ID를 쓰는 팀일 때만 "구현 안 됨"을 본다
        for f, st in sorted(df.items()):
            if f not in fids and "후속" not in st and st != "F02":
                rows.append({"kind": "기능", "item": f, "code": "-", "doc": f"E09 ({st})", "diff": "문서에만 (코드에서 ID를 찾지 못함)"})
    counts = {}
    for r in rows:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    return {"rows": rows, "matched": matched, "counts": counts,
            "code": {"screens": len(code["screens"]), "apis": len(code["apis"]), "feature_ids": len(fids)},
            "docs": {"screens": len(ds), "apis": len(da), "features": len(df)}}


def _rev(root: Path | None) -> str:
    if root is None:
        return ""
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def record(release: str, root: Path | None, no_code: str = "") -> Path:
    docs = ck.load_docs()
    res = compare(None if no_code else scan_code(root), docs)
    OUT.mkdir(parents=True, exist_ok=True)
    day = dt.date.today()
    dest = OUT / f"{release}_{day:%Y%m%d}.md"
    code_desc = f"코드 없음: {no_code}" if no_code else (str(root.relative_to(ROOT)) if root and root.is_relative_to(ROOT) else str(root))
    L = ["---", f"asbuilt: {release}", f"date: {day}", f"code: {code_desc}", f"commit: {_rev(root) or '-'}", "---", "",
         f"# 현행화 {release} ({day})", "",
         "> 출시 후에는 배포된 코드가 기준이고 문서가 따라갑니다. 행마다 **판정**을 채웁니다:",
         "> - `문서 갱신` — 코드가 맞다. 해당 문서(E10·B02·E09·F02)를 고치면 변경 전파가 이어집니다 (`/edpm-change`)",
         "> - `결함` — 문서가 맞다. 결함으로 등록하고 코드를 고칩니다 (`/edpm-spec qa defects`)",
         "> - `의도된 차이` — 둘 다 맞다 (예: 관리자 전용 내부 API). 사유를 적습니다",
         "> 판정이 모두 채워져야 출시 후 마무리 문서(M05·E20)를 완료할 수 있습니다 (G-ASBUILT).", "",
         "## 요약", "", "| 구분 | 코드 | 문서 | 차이 |", "|------|------|------|------|"]
    c, d = res.get("code", {}), res["docs"]
    for k, ck_, dk in (("화면", "screens", "screens"), ("API", "apis", "apis"), ("기능", "feature_ids", "features")):
        L.append(f"| {k} | {c.get(ck_, '-')} | {d.get(dk, '-')} | {res['counts'].get(k, 0)} |")
    L += ["", "## 차이", ""]
    if no_code:
        L += [f"코드를 볼 수 없어 자동 대조를 하지 않았습니다 ({no_code}). 배포된 화면은 `/edpm-change screen <SCR-ID> <URL>`로 하나씩 대조하고, 결과를 아래 표에 적습니다.", "",
              "| # | 종류 | 항목 | 코드 | 문서 | 차이 | 판정 | 조치·사유 |", "|---|------|------|------|------|------|------|-----------|",
              f"| 1 | 화면 | 배포 화면 대조 결과 (SCR별로 행을 추가) | - | E10 | {{대조 결과}} | {PENDING} | |"]
    elif res["rows"]:
        L += ["| # | 종류 | 항목 | 코드 | 문서 | 차이 | 판정 | 조치·사유 |", "|---|------|------|------|------|------|------|-----------|"]
        for i, r in enumerate(res["rows"], 1):
            L.append(f"| {i} | {r['kind']} | {r['item']} | {r['code']} | {r['doc']} | {r['diff']} | {PENDING} | |")
    else:
        L.append("차이 없음.")
    L += ["", f"## 일치 ({len(res['matched'])})", ""] + [f"- {x}" for x in res["matched"][:200]]
    L += ["", "## 현행화 이력", "", "판정 후 고친 문서를 적습니다.", "", "| 문서 | 변경 | 추가 | 삭제 | 날짜 |", "|------|------|------|------|------|", ""]
    dest.write_text("\n".join(L), encoding="utf-8")
    return dest


def records() -> list[dict]:
    out = []
    for p in sorted(OUT.glob("*.md")) if OUT.exists() else []:
        t = ck.read(p)
        fm = ck.parse_frontmatter(t)
        if not fm.get("asbuilt"):
            continue
        out.append({"rel": str(p.relative_to(ROOT)), "release": fm["asbuilt"], "date": fm.get("date", ""),
                    "pending": t.count(PENDING)})
    return out


def main() -> int:
    a = sys.argv[1:]
    if not a or a[0] not in {"scan", "record", "status"}:
        print(__doc__); return 0
    opt = lambda k: a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else ""  # noqa: E731
    if a[0] == "status":
        rs = records()
        if "--json" in a:
            print(json.dumps(rs, ensure_ascii=False, indent=2)); return 0
        if not rs:
            print("현행화 기록 없음 — 출시 후 `/edpm-change asbuilt <릴리스>`"); return 0
        for r in rs:
            print(f"- {r['release']} {r['date']} {r['rel']} — " + (f"판정 안 한 행 {r['pending']}" if r["pending"] else "판정 완료"))
        return 0
    no_code = opt("--no-code")
    root = None if no_code else code_root(opt("--code"))
    if not no_code and (root is None or not root.exists()):
        print("제품 코드를 찾지 못했습니다. `--code <경로>`(개발팀 저장소 등)를 주거나, 코드를 볼 수 없으면 `--no-code \"사유\"`."); return 1
    if a[0] == "scan":
        res = compare(scan_code(root), ck.load_docs())
        if "--json" in a:
            print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
        print(f"# 현행화 대조 ({root})")
        print(f"코드: 화면 {res['code']['screens']}, API {res['code']['apis']}, 기능 ID {res['code']['feature_ids']} / "
              f"문서: 화면 {res['docs']['screens']}, API {res['docs']['apis']}, 기능 {res['docs']['features']}")
        for r in res["rows"]:
            print(f"- [{r['kind']}] {r['item']} — {r['diff']} (코드 {r['code']}, 문서 {r['doc']})")
        if not res["rows"]:
            print("차이 없음")
        return 0
    rel = [x for x in a[1:] if not x.startswith("--") and x not in {opt("--code"), no_code}]
    if not rel:
        print("사용: edpm_asbuilt.py record <릴리스> [--code <경로> | --no-code \"사유\"]"); return 1
    dest = record(rel[0], root, no_code)
    n = ck.read(dest).count(PENDING)
    print(f"현행화 기록: {dest.relative_to(ROOT)} — 판정할 차이 {n}건" + (" (코드 없음: 화면을 /edpm-change screen으로 대조)" if no_code else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
