#!/usr/bin/env python3
"""EdPM 화면설계서: E10의 화면 목록·상태·화면별 구성으로 모든 화면을 HTML 한 장에 (.edpm/screens.html).

사용:
  python3 automation/scripts/edpm_screens.py            # 만들기
  python3 automation/scripts/edpm_screens.py --open     # 만들고 브라우저로 열기
  python3 automation/scripts/edpm_screens.py --json     # 데이터만 출력 (점검용)

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
                                        "priority": "", "areas": [], "entry": "", "desc": "", "links": [], "states": {},
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
        "e10": {"status": e10["status"], "rel": e10["rel"], "url": _editor_url() + e10["path"].resolve().as_posix()},
        "screens": order, "flows": data["flows"], "broken": broken,
        "summary": {"screens": len(order), "with_layout": sum(1 for s in order if s["has_layout"]),
                    "missing_states": sum(1 for s in order if s["missing_states"]), "broken": len(broken),
                    "warns": sum(1 for s in order if s["warns"])},
    })
    return base


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
        print(f"화면설계서: {OUT} (화면 {data['summary'].get('screens', 0)}개)" if data["e10"] else
              f"화면설계서: {OUT} — E10이 아직 없습니다 (/edpm-doc E10)")
    return OUT


def main() -> int:
    if "--json" in sys.argv:
        print(json.dumps(build(), ensure_ascii=False, indent=2))
        return 0
    write("--quiet" in sys.argv)
    if "--open" in sys.argv and sys.platform == "darwin":
        subprocess.run(["open", str(OUT)], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
