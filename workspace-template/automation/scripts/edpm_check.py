#!/usr/bin/env python3
"""EdPM 워크스페이스 결정적 점검기. LLM 없이 frontmatter·CSV·링크를 읽어 상태를 판정한다.

사용:
  python3 automation/scripts/edpm_check.py brief              # 세션 시작용 요약 (SessionStart 훅이 호출)
  python3 automation/scripts/edpm_check.py report             # 전체 점검 표 (/edpm-lint가 먼저 실행)
  python3 automation/scripts/edpm_check.py json               # 같은 내용을 JSON으로
  python3 automation/scripts/edpm_check.py gate <문서 경로>   # 그 문서를 done으로 바꿀 수 있는가 (0 가능 / 1 불가)
  python3 automation/scripts/edpm_check.py pii <파일 경로>    # 식별 정보 패턴 검사 (0 없음 / 1 발견)
  python3 automation/scripts/edpm_check.py next               # 다음에 쓸 수 있는 산출물
  python3 automation/scripts/edpm_check.py phase              # 지금 단계와 다음 할 일 (PRD → 요구사항 → 스펙 → 프로토타입·구현)
  python3 automation/scripts/edpm_check.py progress [--all]   # 진행표 한 장: 문서·상태·완료일·전제·착수 가능 여부
  python3 automation/scripts/edpm_check.py start <문서 경로>  # 이 문서를 지금 써도 되는가 — 전제조건 (0 가능 / 1 불가, 생성 게이트)
  python3 automation/scripts/edpm_check.py code-gate <경로>   # 제품 코드(src/)를 써도 되는가 (G-SPEC, 개발 체계) (0 가능 / 1 불가)

판정 규칙은 AGENTS.md 6절·프레임워크 guide/02와 같다. 여기서 못 보는 게이트(G-CAL 시즌 충돌, G-MEASURE SQL 결과 등)는
/edpm-lint가 LLM으로 보완한다. 표준 라이브러리만 쓴다.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("EDPM_ROOT") or Path(__file__).resolve().parents[2])
DOCS, WIKI, RAW, OPS = ROOT / "03.docs", ROOT / "02.wiki", ROOT / "01.자료실", ROOT / "04.ops"
TODAY = dt.date.today()
STALE_DAYS = 180
DONE = {"done", "n/a"}
PRD_OK = {"review", "done"}      # PRD는 review 이상이면 다른 산출물의 전제 충족 (판을 올리며 계속 다듬는 문서)
REQ_ID = re.compile(r"[A-Z]\d{2}|PRD")

# 게이트: 대상 문서 → [(게이트, [필요 문서], 조건)]. 조건 "present"는 그 문서가 있고 n/a가 아닐 때만 요구.
GATES = {
    "E08": [("G-LEARN", ["E05"], "always")],
    "E09": [("G-LEARN", ["E05"], "always")],
    "E15": [("G-SAFE", ["E13"], "present"), ("G-AI", ["E14", "A10", "A14"], "present:E14"),
            ("G-AI", ["A06"], "present:A03"), ("G-AI", ["A12"], "present:A12")],
    "E18": [("G-EVIDENCE", ["E17"], "always"), ("G-POLICY", ["P01"], "present"),
            ("G-POLICY", ["S07"], "present"), ("G-STAGE", ["N04"], "present:N01")],
    "F03": [("G-IMPACT", ["F02"], "always")],
    "V02": [("G-PROTO", ["V01"], "always")],
}
PII = {
    "휴대전화": re.compile(r"(?<!\d)01[016789][-. ]?\d{3,4}[-. ]?\d{4}(?!\d)"),
    "주민등록번호": re.compile(r"(?<!\d)\d{6}[-]\s?[1-4]\d{6}(?!\d)"),
    "이메일": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
}
# 이메일 예시 표식(줄 단위)과 중괄호 플레이스홀더 구간(매치 단위)만 제외한다.
# 과거 \{.*\} 패턴은 중괄호가 있는 줄 전체를 통과시켜 실제 식별 정보를 놓쳤다.
PII_EMAIL_EXAMPLE = re.compile(r"example\.com|noreply@|\[가명\]")
PII_PLACEHOLDER = re.compile(r"\{[^{}]*\}")


# ---------- frontmatter ----------

def parse_frontmatter(text: str) -> dict:
    """YAML 부분집합: `key: value`, `key: [a, b]`, 주석, 빈 값. 중첩은 다루지 않는다."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    for line in text[3:end].splitlines():
        line = re.sub(r"\s#(\s.*)?$", "", line).rstrip()   # 줄 끝 주석 (공백 한 칸 뒤 #도 주석: `[A01, B01] # 메모`)
        if ":" not in line or line.startswith(" "):
            continue
        k, v = line.split(":", 1)
        v = v.strip().strip('"').strip("'")
        if v.startswith("[") and v.endswith("]"):
            fm[k.strip()] = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
        else:
            fm[k.strip()] = v
    return fm


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def parse_date(s) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s).strip()[:10])
    except (ValueError, TypeError):
        return None


# ---------- 산출물 ----------

def load_docs() -> list[dict]:
    docs = []
    prd = ROOT / "PRD.md"
    if prd.exists():
        fm = parse_frontmatter(read(prd))
        docs.append({"id": "PRD", "path": prd, "rel": "PRD.md", "fm": fm,
                     "status": fm.get("status", "draft") or "draft", "folder": ROOT})
    if not DOCS.exists():
        return docs
    for p in sorted(DOCS.rglob("*.md")):
        if any(part.startswith("_") for part in p.relative_to(DOCS).parts):
            continue  # _과제템플릿, _프로토타입템플릿, _dashboard
        fm = parse_frontmatter(read(p))
        if not fm.get("doc_id"):
            continue
        docs.append({"id": fm["doc_id"], "path": p, "rel": str(p.relative_to(ROOT)), "fm": fm,
                     "status": fm.get("status", "draft") or "draft", "folder": p.parent})
    return docs


def find(docs: list[dict], doc_id: str, near: Path | None = None) -> dict | None:
    """같은 폴더(과제·프로토타입 단위) 우선, 없으면 전역에서 찾는다. 여러 개면 done인 것을 우선."""
    cands = [d for d in docs if d["id"] == doc_id]
    if near is not None:
        local = [d for d in cands if d["folder"] == near]
        if local:
            cands = local
    cands.sort(key=lambda d: d["status"] not in DONE)
    return cands[0] if cands else None


def _table_rows(text: str, header_substr: str) -> list[list[str]]:
    """header_substr를 포함한 제목 다음 첫 마크다운 표의 데이터 행(헤더·구분선 제외)."""
    lines = text.splitlines()
    start = None
    for idx, ln in enumerate(lines):
        if ln.lstrip().startswith("#") and header_substr in ln:
            start = idx + 1
            break
    if start is None:
        return []
    rows, seen = [], False
    for ln in lines[start:]:
        s = ln.strip()
        if s.startswith("#"):
            if seen:
                break
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue  # 구분선
            seen = True
            rows.append(cells)
        elif seen and s:
            break
    return rows[1:] if len(rows) > 1 else []


def gmeasure_ok(f02_text: str) -> bool:
    """F02 목표 지표에 예시·플레이스홀더가 아닌, 기준선·목표가 채워진 행이 하나라도 있는가 (G-MEASURE)."""
    for cells in _table_rows(f02_text, "목표 지표"):
        j = " ".join(cells)
        if "예시" in j or "{" in j:
            continue
        if len(cells) >= 7:
            if cells[3] and cells[4] and cells[6]:
                return True
        elif any(cells):
            return True
    return False


def gimpact_unresolved(f02_text: str) -> int:
    """F02 영향 점검표에서 미처리(해당여부 미기재 또는 '해당'인데 완료 미체크) 행 수 (G-IMPACT)."""
    bad = 0
    for cells in _table_rows(f02_text, "영향 점검"):
        if len(cells) < 5:
            continue
        if "예시" in " ".join(cells):
            continue
        applies, done = cells[1], cells[-1]
        if not applies or "{" in applies:
            bad += 1
        elif "없음" not in applies and "n/a" not in applies.lower() and not re.search(r"\[[xX]\]", done):
            bad += 1
    return bad


def gate_check(doc: dict, docs: list[dict], content: bool = True) -> list[str]:
    """done 전환을 막는 사유 목록. 비어 있으면 통과. content=False면 본문 게이트(G-MEASURE·G-IMPACT)는 건너뛴다(착수 가능 판정용)."""
    reasons = []
    if doc["id"] not in {"E00", "PRD"}:
        prd = find(docs, "PRD")
        if prd is None:
            reasons.append("G-PRD: PRD.md 없음 — 모든 산출물은 PRD에서 출발합니다 (/edpm-prd)")
        elif prd["status"] not in PRD_OK:
            reasons.append(f"G-PRD: PRD status={prd['status']} (review 이상 필요)")
    for req in doc["fm"].get("requires", []) or []:
        req = req.split("(")[0].strip()
        if not REQ_ID.fullmatch(req) or req == "PRD":
            continue  # PRD는 위 G-PRD로 판정, "+테스트 기록" 같은 설명은 실체 검증 대상 (lint)
        r = find(docs, req, doc["folder"])
        if r is None:
            reasons.append(f"전제 {req}: 문서 없음")
        elif r["status"] not in DONE:
            reasons.append(f"전제 {req}: status={r['status']}")
    for gate, reqs, cond in GATES.get(doc["id"], []):
        if cond.startswith("present"):
            key = cond.split(":")[1] if ":" in cond else reqs[0]
            k = find(docs, key, doc["folder"])
            if k is None or k["status"] == "n/a":
                continue
        for req in reqs:
            r = find(docs, req, doc["folder"])
            if r is None:
                reasons.append(f"{gate}: {req} 문서 없음")
            elif r["status"] not in DONE:
                reasons.append(f"{gate}: {req} status={r['status']}")
    if content:
        if doc["id"] == "F02" and not gmeasure_ok(read(doc["path"])):
            reasons.append("G-MEASURE: 목표 지표에 기준선·목표·SQL이 채워진 실제 행이 없음")
        if doc["id"] == "F03":
            f02 = find(docs, "F02", doc["folder"])
            if f02 is not None:
                n = gimpact_unresolved(read(f02["path"]))
                if n:
                    reasons.append(f"G-IMPACT: F02 영향 점검표 미처리 {n}행")
    return reasons


def prd_ready(docs: list[dict]) -> bool:
    p = find(docs, "PRD")
    return p is not None and p["status"] in PRD_OK


def start_check(doc: dict, docs: list[dict]) -> list[str]:
    """생성 게이트: 이 산출물의 본문을 지금 써도 되는가. A(전제)가 끝나야 B를 쓴다.
    done 게이트(gate_check)와 달리 본문·출시 게이트(G-SAFE 등)는 보지 않고 G-PRD와 전제조건만 본다."""
    reasons = []
    if doc["id"] not in {"E00", "PRD"}:
        prd = find(docs, "PRD")
        if prd is None or prd["status"] not in PRD_OK:
            reasons.append("G-PRD: PRD가 review 이상이어야 다른 산출물을 씁니다 (/edpm-prd)")
    for req in doc["fm"].get("requires", []) or []:
        req = req.split("(")[0].strip()
        if not REQ_ID.fullmatch(req) or req == "PRD":
            continue
        r = find(docs, req, doc["folder"])
        if r is None:
            reasons.append(f"전제 {req}: 문서 없음")
        elif r["status"] not in DONE:
            reasons.append(f"전제 {req}: status={r['status']}")
    return reasons


CHAIN_ORDER = ["E00", "PRD"] + [f"E{i:02d}" for i in range(1, 21)]
TRACK_ORDER = "MNVFALPSB"


def _order(d: dict) -> tuple:
    did = d["id"]
    if did in CHAIN_ORDER:
        return (0, CHAIN_ORDER.index(did), d["rel"])
    t = TRACK_ORDER.find(did[0]) if did else 99
    return (1, t if t >= 0 else 99, did, d["rel"])


def progress_rows(docs: list[dict], show_all: bool = False) -> list[dict]:
    rows = []
    for d in sorted(docs, key=_order):
        if d["status"] == "n/a" and not show_all:
            continue
        reqs = ", ".join(r.split("(")[0].strip() for r in (d["fm"].get("requires") or []) if REQ_ID.fullmatch(r.split("(")[0].strip())) or "-"
        if d["status"] == "done" or (d["id"] == "PRD" and d["status"] in PRD_OK):
            state = "완료" if d["status"] == "done" else "검토 중 (다음 단계 열림)"
        elif d["status"] == "n/a":
            state = f"해당없음 — {d['fm'].get('na_reason', '')}".rstrip(" —")
        else:
            block = start_check(d, docs)
            early = (d["fm"].get("early_draft") or "").strip()
            if not block:
                state = "착수 가능" if d["status"] == "draft" else "검토 중"
            elif early:
                state = f"미리 초안 ({early})"
            else:
                state = "대기: " + "; ".join(b.split(":")[0] for b in block)
        rows.append({"id": d["id"], "title": d["fm"].get("title", ""), "status": d["status"], "requires": reqs,
                     "done_date": d["fm"].get("updated", "") if d["status"] == "done" else "-", "state": state, "rel": d["rel"]})
    return rows


def fmt_progress(docs: list[dict], show_all: bool = False) -> str:
    rows = progress_rows(docs, show_all)
    na = len([d for d in docs if d["status"] == "n/a"])
    ph = phase(docs)
    L = [f"# 진행표 {TODAY}", f"지금 단계: {ph['step']} — 다음: {ph['do'][0].split(' — ')[0]}", "",
         "| ID | 산출물 | 상태 | 완료일 | 전제조건 | 지금 |", "|----|--------|------|--------|----------|------|"]
    L += [f"| {r['id']} | {r['title']} | {r['status']} | {r['done_date']} | {r['requires']} | {r['state']} |" for r in rows]
    if na and not show_all:
        L.append(f"\n해당없음(n/a) {na}건은 숨김 — 모두 보려면 `progress --all`")
    return "\n".join(L)


def next_docs(docs: list[dict]) -> list[dict]:
    """착수 가능한 산출물. PRD가 준비되기 전에는 E00·PRD만. 전제가 모두 n/a·없음뿐인 문서는 제외
    (예: E19가 n/a라서 E20 회고가 시작 시점부터 뜨는 문제)."""
    if not prd_ready(docs):
        return [d for d in docs if d["id"] in {"E00", "PRD"} and d["status"] not in DONE | PRD_OK]
    out = []
    for d in docs:
        if d["status"] in DONE or (d["id"] == "PRD" and d["status"] in PRD_OK):
            continue
        reqs = [r.split("(")[0].strip() for r in d["fm"].get("requires", []) or []]
        reqs = [r for r in reqs if REQ_ID.fullmatch(r)]
        if reqs:
            real = [find(docs, r, d["folder"]) for r in reqs]
            if not any(x is not None and (x["status"] == "done" or (x["id"] == "PRD" and x["status"] in PRD_OK)) for x in real):
                continue
        if not gate_check(d, docs, content=False):
            out.append(d)
    return out


# ---------- 단계 (지금 어디인가, 다음 할 일) ----------

def dev_system() -> str:
    """AGENTS.md 2절 '개발 체계': 개발팀 / 바이브코딩 / 미정"""
    m = re.search(r"^\| 개발 체계 \| (.+?) \|", read(ROOT / "AGENTS.md"), re.M)
    v = m.group(1) if m else ""
    if v.startswith("{") or not v:
        return "미정"
    return "바이브코딩" if "바이브" in v else ("개발팀" if "개발팀" in v else "미정")


def work_mode() -> str:
    m = re.search(r"^\| 업무 모드 \| (.+?) \|", read(ROOT / "AGENTS.md"), re.M)
    v = (m.group(1) if m else "")
    if v.startswith("{"):
        return ""
    return ("N" if "N" in v.split("—")[0] or "신사업" in v else "") + ("F" if "F " in v or "운영 개선" in v else "")


def spec_ok(docs: list[dict]) -> bool:
    e09 = [d for d in docs if d["id"] == "E09"]
    return any(d["status"] == "done" or (d["fm"].get("gate_skip") or "").strip() for d in e09)


def spec_tasks(docs: list[dict]) -> dict:
    out = {}
    for d in docs:
        if d["id"] == "E09":
            for cells in _table_rows(read(d["path"]), "작업 분해"):
                j = " ".join(cells)
                if "예시" in j or "{" in j or not cells or not cells[0]:
                    continue
                st = cells[-1] or "예정"
                out[st] = out.get(st, 0) + 1
    return out


def _st(docs, did):
    d = find(docs, did)
    return d["status"] if d else None


def phase(docs: list[dict]) -> dict:
    """프레임워크 흐름상 지금 단계와 다음 할 일. 순서: 시작 → PRD → (탐색·진단·착수) → 상세 요구사항 → 스펙 → 프로토타입·구현 → 출시."""
    mode, dev = work_mode(), dev_system()
    st = lambda i: _st(docs, i)  # noqa: E731
    open_ = lambda i: st(i) not in (None, "done", "n/a")  # noqa: E731
    if st("E00") != "done":
        return {"step": "0 시작", "why": "회사·제품 프로필(E00)이 아직 없습니다", "do": ["/edpm-start — 무엇을 하려는지 묻고 길을 안내", "/edpm-init — 회사·제품 인터뷰"]}
    if not prd_ready(docs):
        why = "PRD.md가 없습니다" if st("PRD") is None else f"PRD가 {st('PRD')}입니다"
        return {"step": "1 PRD", "why": why + ". 모든 산출물·프로토타입·코드는 PRD에서 출발합니다 (만들 제품 전체를 정의)",
                "do": ["/edpm-prd — 인터뷰로 작성하거나 기존 기획서를 PRD로 정리", "검토 후 PRD status를 review로"]}
    todo = []
    if "N" in mode and open_("N01"):
        todo.append("/edpm-venture opportunity — N01 사업기회 (PRD 2절 근거 보강)")
    if "F" in mode and open_("F00"):
        todo.append("/edpm-feature baseline — F00 서비스 현황 진단")
    if open_("M01"):
        todo.append("/edpm-report M01 — 착수보고서 (PRD 8절 릴리스 계획 → 일정)")
    if todo:
        return {"step": "2 착수·근거", "why": "PRD를 근거와 일정으로 받칩니다", "do": todo}
    if open_("E06"):
        miss = gate_check(find(docs, "E06"), docs, content=False)
        return {"step": "3 상세 요구사항", "why": "PRD 5·7절을 REQ와 인수조건으로 쪼갭니다" + (f" (먼저: {', '.join(m.split(':')[0] for m in miss)})" if miss else ""),
                "do": ["/edpm-doc E06"] + [f"/edpm-doc {m.split(':')[0].replace('전제 ', '')}" for m in miss if m.startswith("전제")][:3]}
    if open_("E09"):
        return {"step": "4 스펙", "why": "E09 기능명세 = 스펙: 기능·인수조건·입출력 계약·작업(T)·테스트. 승인 전에는 제품 코드를 쓰지 않습니다 (G-SPEC)",
                "do": ["/edpm-spec write", "/edpm-spec check"]}
    tasks = spec_tasks(docs)
    if dev == "바이브코딩":
        left = sum(v for k, v in tasks.items() if k != "완료")
        step = {"step": "5 구현 (바이브코딩)", "why": f"스펙 작업 {sum(tasks.values())}건 중 미완료 {left}건" if tasks else "스펙 7절 작업 표가 비어 있습니다",
                "do": ["/edpm-spec build T-xx — 작업 하나씩 구현·테스트", "/edpm-proto — PRD 9절 정수를 먼저 보여줄 때"]}
    else:
        step = {"step": "5 프로토타입·이관", "why": "PRD 9절의 정수를 프로토타입으로 보여주고, 스펙을 개발팀에 넘깁니다" + (" (AGENTS.md 2절 개발 체계 미정)" if dev == "미정" else ""),
                "do": ["/edpm-proto new — PRD 9절 정수", "/edpm-handoff dev — 스펙 이관"]}
    # 출시 준비로 넘어가는 신호: 스펙 작업이 있고 모두 완료, 또는 릴리즈·파일럿 문서 작업이 시작됨
    built = bool(tasks) and not any(k != "완료" for k in tasks)
    started = any(st(i) in ("review", "done") for i in ("E15", "E17"))
    for did, cmd in (("E15", "/edpm-doc E15 — 릴리즈 계획"), ("E18", "/edpm-doc E18 — 도입·출시 계획")):
        if open_(did) and (built or started):
            return {"step": "6 출시 준비", "why": "구현·검증이 끝나면 출시 게이트(G-SAFE·G-AI·G-EVIDENCE)를 통과합니다", "do": [cmd]}
    return step


def code_gate(path: Path, docs: list[dict]) -> tuple[bool, str]:
    """제품 코드(src/) 쓰기 판정 (G-SPEC)."""
    try:
        rel = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return True, "워크스페이스 밖"
    if not rel.parts or rel.parts[0] != "src" or rel.name == "README.md":
        return True, "제품 코드 아님"
    dev = dev_system()
    if dev == "개발팀":
        return False, ("개발 체계가 '개발팀'입니다. 제품 코드는 개발팀 몫이고 PM은 스펙을 넘깁니다 (/edpm-handoff dev). "
                       "PM이 직접 구현하는 프로젝트면 AGENTS.md 2절 개발 체계를 '바이브코딩'으로 바꿉니다. 검증용 코드는 06.prototypes/에.")
    if not prd_ready(docs):
        return False, "G-PRD: PRD.md가 review 이상이어야 제품 코드를 씁니다 (/edpm-prd)"
    if not spec_ok(docs):
        return False, ("G-SPEC: 스펙(E09 기능명세)이 done이 아닙니다. 스펙을 먼저 확정합니다 (/edpm-spec write → 승인). "
                       "검증용 spike는 06.prototypes/PT-xx에 V01과 함께. 사용자가 명시적으로 허용하면 E09에 gate_skip 사유")
    return True, "스펙 승인됨"


# ---------- 위키 ----------

def wiki_index() -> set[str]:
    names = set()
    for p in WIKI.rglob("*.md") if WIKI.exists() else []:
        rel = p.relative_to(WIKI).with_suffix("")
        names.add(str(rel)); names.add(rel.name)
    for p in RAW.rglob("*") if RAW.exists() else []:
        if p.is_file():
            rel = p.relative_to(ROOT)
            names.add(str(rel)); names.add(str(rel.with_suffix(""))); names.add(p.stem)
    for p in DOCS.rglob("*.md") if DOCS.exists() else []:
        rel = p.relative_to(ROOT)
        names.add(str(rel.with_suffix(""))); names.add(p.stem)
    return names


LINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def broken_links() -> list[tuple[str, str]]:
    names = wiki_index()
    out = []
    for base in (WIKI, DOCS):
        for p in base.rglob("*.md") if base.exists() else []:
            if p.name.startswith("_") or "_템플릿" in str(p):
                continue
            for line in read(p).splitlines():
                if "예시" in line or "예:" in line or "{" in line or "..." in line:
                    continue  # 템플릿 예시 행·자리표시자
                for m in LINK.finditer(line):
                    t = m.group(1).strip()
                    if t in names or t.removeprefix("02.wiki/") in names or t.split("/")[-1] in names:
                        continue
                    if "…" in t or "xx" in t.lower() or "0x" in t or t in {"경로/페이지", "페이지"}:
                        continue
                    out.append((str(p.relative_to(ROOT)), t))
    return out


def stale_pages() -> list[tuple[str, str]]:
    out = []
    for p in WIKI.rglob("*.md") if WIKI.exists() else []:
        fm = parse_frontmatter(read(p))
        if fm.get("type") in {"regulation", "standard", "competitor", "metric"} or fm.get("verified"):
            v = parse_date(fm.get("verified"))
            if v and (TODAY - v).days > STALE_DAYS and fm.get("status") != "stale":
                out.append((str(p.relative_to(ROOT)), str(v)))
    return out


# ---------- 개인정보 ----------

def pii_scan_text(text: str) -> list[tuple[str, str]]:
    hits = []
    for line in text.splitlines():
        masked = PII_PLACEHOLDER.sub(lambda m: " " * len(m.group(0)), line)  # {…} 플레이스홀더 구간만 비운다
        for name, rx in PII.items():
            for m in rx.finditer(masked):
                if name == "이메일" and PII_EMAIL_EXAMPLE.search(line):
                    continue
                hits.append((name, m.group(0)))
    return hits


def pii_scan() -> list[tuple[str, str, str]]:
    out = []
    for base in (RAW, WIKI):
        for p in base.rglob("*") if base.exists() else []:
            if not p.is_file() or p.suffix.lower() not in {".md", ".txt", ".csv", ".json"} or p.name.startswith("_"):
                continue
            for name, val in pii_scan_text(read(p))[:3]:
                out.append((str(p.relative_to(ROOT)), name, val[:4] + "…"))
    return out


# ---------- 일정·프로토타입·결정·회의 ----------

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if not (r.get("이름") or r.get("비고") or "").startswith("(예시)")
                and "예시" not in (r.get("비고") or "")]


def wbs_status() -> dict:
    rows = read_csv(DOCS / "M.관리" / "M02_WBS.csv")
    rows = [r for r in rows if r.get("wp_id")]
    overdue = [r for r in rows if r.get("상태") != "완료" and (parse_date(r.get("종료")) or TODAY) < TODAY]
    soon = [r for r in rows if r.get("상태") != "완료" and parse_date(r.get("종료"))
            and TODAY <= parse_date(r["종료"]) <= TODAY + dt.timedelta(days=7)]
    done = len([r for r in rows if r.get("상태") == "완료"])
    unlinked = [r for r in rows if not (r.get("이슈") or "").strip()]
    return {"total": len(rows), "done": done, "overdue": overdue, "soon": soon, "unlinked": len(unlinked)}


def proto_status() -> dict:
    rows = read_csv(DOCS / "V.프로토타입" / "프로토타입목록.csv")
    overdue = [r for r in rows if r.get("상태") in {"계획", "진행", "빌드", "테스트"}
               and (parse_date(r.get("종료")) or TODAY) < TODAY]
    undecided = [r for r in rows if r.get("상태") in {"테스트완료", "완료"} and not (r.get("결정") or "").strip()]
    active = [r for r in rows if r.get("상태") not in {"결정완료", "폐기", ""}]
    return {"active": active, "overdue": overdue, "undecided": undecided}


def decisions_due() -> list[dict]:
    out = []
    d = WIKI / "decisions"
    for p in sorted(d.glob("ADR-*.md")) if d.exists() else []:
        fm = parse_frontmatter(read(p))
        rv = parse_date(fm.get("review_date"))
        if rv and rv <= TODAY and not (fm.get("outcome") or "").strip():
            out.append({"id": fm.get("adr_id", p.stem), "title": fm.get("title", ""), "review": str(rv), "path": str(p.relative_to(ROOT))})
    return out


def meetings_pending() -> list[str]:
    d = OPS / "회의록"
    out = []
    for p in sorted(d.glob("*.md")) if d.exists() else []:
        if p.name.startswith("_"):
            continue
        if parse_frontmatter(read(p)).get("ingest", "pending") == "pending":
            out.append(p.name)
    return out


def agents_context() -> dict:
    s = read(ROOT / "AGENTS.md")
    out = {}
    for key in ("회사·제품", "업무 모드", "서비스 유형", "개발 체계", "일정 관리 도구"):
        m = re.search(rf"^\| {re.escape(key)} \| (.+?) \|", s, re.M)
        if m and not m.group(1).startswith("{"):
            out[key] = re.sub(r"\s*[—(].*$", "", m.group(1))[:60]
    return out


# ---------- 조립 ----------

def collect() -> dict:
    docs = load_docs()
    by_status = {}
    for d in docs:
        by_status[d["status"]] = by_status.get(d["status"], 0) + 1
    skipped = [d for d in docs if (d["fm"].get("gate_skip") or "").strip()]
    bad_fm = [d["rel"] for d in docs if d["status"] not in {"draft", "review", "done", "n/a"}
              or not parse_date(d["fm"].get("updated")) and d["status"] in DONE]
    return {
        "today": str(TODAY), "context": agents_context(), "phase": phase(docs),
        "docs": {"total": len(docs), "by_status": by_status,
                 "review": [d["rel"] for d in docs if d["status"] == "review"],
                 "next": [f"{d['id']} {d['rel']}" for d in next_docs(docs)][:12],
                 "gate_skip": [f"{d['id']} — {d['fm']['gate_skip']}" for d in skipped],
                 "early_draft": [f"{d['id']} — {d['fm']['early_draft']}" for d in docs
                                 if (d["fm"].get("early_draft") or "").strip() and d["status"] not in DONE],
                 "blocked_done": [f"{d['id']}: {'; '.join(gate_check(d, docs))}" for d in docs
                                   if d["status"] in DONE and d["status"] != "n/a" and gate_check(d, docs)],
                 "bad_frontmatter": bad_fm},
        "wiki": {"broken_links": broken_links()[:20], "stale": stale_pages()[:20]},
        "pii": pii_scan()[:20],
        "wbs": wbs_status(), "proto": proto_status(), "decisions_due": decisions_due(),
        "meetings_pending": meetings_pending(),
    }


def fmt_brief(r: dict) -> str:
    L = [f"# EdPM 상황판 {r['today']}"]
    ctx = r["context"]
    if ctx:
        L.append(" · ".join(f"{k}: {v}" for k, v in ctx.items()))
    ph = r["phase"]
    if ph["step"] == "0 시작":
        L += ["", "## 처음 오셨군요",
              "이 워크스페이스는 PRD에서 출발해 요구사항 → 스펙 → 프로토타입·구현으로 갑니다. 세 단계로 시작합니다.",
              "1. `/edpm-start` — 무엇을 하려는지(신사업 / 운영 중 서비스 개선 / 기존 기획서 있음) 묻고 길을 안내합니다",
              "2. `/edpm-init` — 회사·제품 인터뷰 (20~30분)",
              "3. `/edpm-prd` — 만들 제품 전체를 PRD로 정의",
              "자세한 순서: 프레임워크 `guide/14.AtoZ사용가이드.md`. 슬래시 명령을 몰라도 \"처음인데 뭐부터 해?\"라고 말하면 됩니다."]
    L += ["", f"## 지금 단계: {ph['step']}", ph["why"]] + [f"- 다음: `{x.split(' — ')[0]}`" + (f" — {x.split(' — ', 1)[1]}" if " — " in x else "") for x in ph["do"]]
    d, w, p = r["docs"], r["wbs"], r["proto"]
    L.append(f"\n산출물 {d['total']}건: " + ", ".join(f"{k} {v}" for k, v in sorted(d["by_status"].items())))
    attention = []
    if d["blocked_done"]:
        attention.append(f"게이트 미충족인데 done: {len(d['blocked_done'])}건 → " + d["blocked_done"][0])
    if d["gate_skip"]:
        attention.append(f"게이트 스킵 {len(d['gate_skip'])}건")
    if d.get("early_draft"):
        attention.append(f"전제 전에 미리 쓴 초안 {len(d['early_draft'])}건: " + ", ".join(x.split(' — ')[0] for x in d["early_draft"][:4]))
    if d["review"]:
        attention.append(f"검토 대기(review) {len(d['review'])}건: " + ", ".join(Path(x).stem.split('_')[0] for x in d["review"][:5]))
    if w["overdue"]:
        attention.append(f"종료일 지난 WP {len(w['overdue'])}건: " + ", ".join(x['wp_id'] for x in w["overdue"][:4]))
    if w["soon"]:
        attention.append(f"7일 내 마감 WP {len(w['soon'])}건: " + ", ".join(x['wp_id'] for x in w["soon"][:4]))
    if p["overdue"]:
        attention.append(f"timebox 지난 프로토타입: " + ", ".join(x['PT'] for x in p["overdue"]))
    if p["undecided"]:
        attention.append(f"결정 안 한 프로토타입: " + ", ".join(x['PT'] for x in p["undecided"]))
    if r["decisions_due"]:
        attention.append(f"재검토일 지난 결정 {len(r['decisions_due'])}건: " + ", ".join(x['id'] for x in r["decisions_due"][:3]) + " → /edpm-decide review")
    if r["meetings_pending"]:
        attention.append(f"위키 반영 안 된 회의록 {len(r['meetings_pending'])}건 → /edpm-meeting ingest")
    if r["pii"]:
        attention.append(f"식별 정보 의심 {len(r['pii'])}곳 (G-PII) → /edpm-lint pii")
    if r["wiki"]["stale"]:
        attention.append(f"180일 넘은 규제·가격 페이지 {len(r['wiki']['stale'])}건")
    if r["wiki"]["broken_links"]:
        attention.append(f"끊긴 링크 {len(r['wiki']['broken_links'])}곳")
    if d["bad_frontmatter"]:
        attention.append(f"frontmatter 오류 {len(d['bad_frontmatter'])}건")
    L.append("\n## 주의" if attention else "\n주의할 항목 없음.")
    L += [f"- {a}" for a in attention]
    if d["next"]:
        L.append("\n## 지금 쓸 수 있는 산출물 (전제조건 충족)")
        L += [f"- {x}" for x in d["next"][:8]]
    L.append("\n전체 진행표: `python3 automation/scripts/edpm_check.py progress`")
    if w["total"]:
        L.append(f"\nWBS {w['done']}/{w['total']} 완료" + (f", 도구 미연결 WP {w['unlinked']}" if w["unlinked"] else ""))
    if p["active"]:
        L.append("프로토타입 진행 중: " + ", ".join(f"{x['PT']}({x['상태']})" for x in p["active"]))
    return "\n".join(L)


def fmt_report(r: dict) -> str:
    L = [fmt_brief(r), "\n## 상세"]
    def sec(title, items, fn=str):
        L.append(f"\n### {title} ({len(items)})")
        L += [f"- {fn(x)}" for x in items] or ["- 없음"]
    sec("게이트 미충족 done", r["docs"]["blocked_done"])
    sec("게이트 스킵", r["docs"]["gate_skip"])
    sec("frontmatter 오류 (status 값, done인데 updated 없음)", r["docs"]["bad_frontmatter"])
    sec("끊긴 링크", r["wiki"]["broken_links"], lambda x: f"{x[0]} → [[{x[1]}]]")
    sec("오래된 페이지 (verified 180일 초과)", r["wiki"]["stale"], lambda x: f"{x[0]} (verified {x[1]})")
    sec("식별 정보 의심", r["pii"], lambda x: f"{x[0]}: {x[1]} {x[2]}")
    sec("종료일 지난 WP", r["wbs"]["overdue"], lambda x: f"{x['wp_id']} {x.get('이름','')} (종료 {x.get('종료','')}, {x.get('상태','')})")
    sec("timebox 지난 프로토타입", r["proto"]["overdue"], lambda x: f"{x['PT']} {x.get('이름','')} (종료 {x.get('종료','')})")
    sec("재검토일 지난 결정", r["decisions_due"], lambda x: f"{x['id']} {x['title']} (재검토 {x['review']})")
    sec("위키 반영 대기 회의록", r["meetings_pending"])
    return "\n".join(L)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "brief"
    if cmd == "gate":
        path = Path(sys.argv[2]).resolve()
        docs = load_docs()
        doc = next((d for d in docs if d["path"] == path), None)
        if doc is None:
            fm = parse_frontmatter(read(path))
            if not fm.get("doc_id"):
                print("doc_id가 없는 파일입니다. 게이트 대상이 아닙니다."); return 0
            doc = {"id": fm["doc_id"], "path": path, "rel": str(path), "fm": fm, "status": fm.get("status", "draft"), "folder": path.parent}
        reasons = gate_check(doc, docs)
        if reasons:
            print(f"{doc['id']} done 불가:\n- " + "\n- ".join(reasons)); return 1
        print(f"{doc['id']} done 가능"); return 0
    if cmd == "pii":
        hits = pii_scan_text(read(Path(sys.argv[2])))
        if hits:
            print("식별 정보 의심: " + ", ".join(f"{n}({v[:4]}…)" for n, v in hits[:5])); return 1
        print("식별 정보 없음"); return 0
    if cmd == "start":
        path = Path(sys.argv[2]).resolve()
        docs = load_docs()
        fm = parse_frontmatter(read(path))
        if not fm.get("doc_id"):
            print("doc_id가 없는 파일입니다. 생성 게이트 대상이 아닙니다."); return 0
        real = next((d for d in docs if d["path"] == path), None)
        folder = real["folder"] if real else path.parent
        doc = {"id": fm["doc_id"], "path": path, "rel": str(path), "fm": fm, "status": fm.get("status", "draft"), "folder": folder}
        reasons = start_check(doc, docs)
        if reasons:
            print(f"{doc['id']}는 아직 쓸 수 없습니다 (A가 끝나야 B):\n- " + "\n- ".join(reasons)); return 1
        print(f"{doc['id']} 착수 가능"); return 0
    if cmd == "progress":
        print(fmt_progress(load_docs(), show_all="--all" in sys.argv)); return 0
    if cmd == "code-gate":
        ok, msg = code_gate(Path(sys.argv[2]), load_docs())
        print(msg)
        return 0 if ok else 1
    r = collect()
    if cmd == "json":
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
    elif cmd == "report":
        print(fmt_report(r))
    elif cmd == "phase":
        ph = r["phase"]
        print(f"지금 단계: {ph['step']}\n{ph['why']}\n" + "\n".join(f"- {x}" for x in ph["do"]))
    elif cmd == "next":
        print("\n".join(r["docs"]["next"]) or "전제조건을 충족한 미완료 산출물이 없습니다.")
    else:
        print(fmt_brief(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
