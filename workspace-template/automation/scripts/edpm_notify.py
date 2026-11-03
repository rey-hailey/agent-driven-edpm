#!/usr/bin/env python3
"""EdPM 알림: 상황판·주간보고·사건을 팀 채널(Slack·Teams)로 보낸다. 대시보드는 PM 혼자 보지만, 진행은 팀이 알아야 한다.

사용:
  python3 automation/scripts/edpm_notify.py brief                 # 보낼 내용 미리보기 (기본, 보내지 않음)
  python3 automation/scripts/edpm_notify.py brief --send          # 실제로 보냄
  python3 automation/scripts/edpm_notify.py weekly <주간보고.md> --send
  python3 automation/scripts/edpm_notify.py event "PT-01 V03 결정: MVP 확장" --send

웹훅 주소는 비밀값이라 파일에 쓰지 않고 환경변수로만 받는다:
  EDPM_SLACK_WEBHOOK  Slack Incoming Webhook URL
  EDPM_TEAMS_WEBHOOK  Teams Incoming Webhook / Workflows URL
둘 다 있으면 둘 다 보낸다. 보내는 내용에는 회사 기밀 수치·학생 정보를 넣지 않는다 (상황판 요약과 문서 ID·제목만).
평일 아침 자동 발송은 .github/workflows/edpm-brief.yml (GitHub Actions 예약, Claude 없이 점검기만 실행).
표준 라이브러리만 쓴다.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edpm_check as ck  # noqa: E402


def brief_text() -> str:
    r = ck.collect()
    ctx = r["context"]
    ph = r["phase"]
    d = r["docs"]
    L = [f"*EdPM 상황판 {r['today']}*" + (f" · {ctx.get('회사·제품')}" if ctx.get("회사·제품") else ""),
         f"지금 단계: *{ph['step']}*"]
    L += [f"• 다음: `{x.split(' — ')[0]}`" + (f" — {x.split(' — ', 1)[1]}" if " — " in x else "") for x in ph["do"][:3]]
    L.append("산출물: " + ", ".join(f"{k} {v}" for k, v in sorted(d["by_status"].items())))
    att = []
    if d["review"]:
        att.append(f"검토 대기 {len(d['review'])}건: " + ", ".join(Path(x).stem.split('_')[0] for x in d["review"][:5]))
    if d["blocked_done"]:
        att.append(f"게이트 미충족인데 done {len(d['blocked_done'])}건")
    if r["wbs"]["overdue"]:
        att.append(f"종료일 지난 작업 {len(r['wbs']['overdue'])}건: " + ", ".join(x["wp_id"] for x in r["wbs"]["overdue"][:4]))
    if r["wbs"]["soon"]:
        att.append(f"7일 내 마감 {len(r['wbs']['soon'])}건: " + ", ".join(x["wp_id"] for x in r["wbs"]["soon"][:4]))
    if r["proto"]["undecided"]:
        att.append("결정 안 한 프로토타입: " + ", ".join(x["PT"] for x in r["proto"]["undecided"]))
    if r["decisions_due"]:
        att.append("재검토일 지난 결정: " + ", ".join(x["id"] for x in r["decisions_due"][:3]))
    if r.get("unknowns_pending"):
        att.append(f"다음 사이클로 넘기지 않은 '아직 모르는 것' {len(r['unknowns_pending'])}건")
    if r["pii"]:
        att.append(f"식별 정보 의심 {len(r['pii'])}곳 — 확인 필요")
    L += (["주의:"] + [f"• {a}" for a in att]) if att else ["주의할 항목 없음"]
    return "\n".join(L)


def weekly_text(path: Path) -> str:
    s = ck.read(path)
    s = re.sub(r"\A---\n.*?\n---\n", "", s, flags=re.S).strip()
    lines = [ln for ln in s.splitlines() if ln.strip() and not ln.startswith(">")]
    head = lines[:18]
    more = len(lines) - len(head)
    return "\n".join(head) + (f"\n… (전체 {len(lines)}줄, 원문: {path.relative_to(ck.ROOT) if path.is_relative_to(ck.ROOT) else path})" if more > 0 else "")


def payloads(text: str) -> list[tuple[str, str, dict]]:
    out = []
    slack, teams = os.environ.get("EDPM_SLACK_WEBHOOK"), os.environ.get("EDPM_TEAMS_WEBHOOK")
    if slack:
        out.append(("Slack", slack, {"text": text}))
    if teams:
        out.append(("Teams", teams, {"text": text.replace("*", "**").replace("\n", "  \n")}))
    return out


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"brief", "weekly", "event"}:
        print(__doc__); return 1
    kind = sys.argv[1]
    if kind == "brief":
        text = brief_text()
    elif kind == "weekly":
        if len(sys.argv) < 3 or sys.argv[2].startswith("--"):
            print("사용: edpm_notify.py weekly <주간보고.md> [--send]"); return 1
        text = weekly_text(Path(sys.argv[2]).resolve())
    else:
        if len(sys.argv) < 3 or sys.argv[2].startswith("--"):
            print('사용: edpm_notify.py event "<내용>" [--send]'); return 1
        text = f"*EdPM* {sys.argv[2]}"
    hits = ck.pii_scan_text(text)
    if hits:
        print("중단: 보낼 내용에 식별 정보로 보이는 값이 있습니다 (G-PII). 가명 처리 후 다시 보내세요."); return 2
    targets = payloads(text)
    if "--send" not in sys.argv:
        print("[미리보기 — 보내지 않음. 보내려면 --send]\n")
        print(text)
        print("\n받는 곳: " + (", ".join(t[0] for t in targets) if targets else "없음 (EDPM_SLACK_WEBHOOK / EDPM_TEAMS_WEBHOOK 환경변수)"))
        return 0
    if not targets:
        print("받는 곳이 없습니다. EDPM_SLACK_WEBHOOK 또는 EDPM_TEAMS_WEBHOOK 환경변수를 설정하세요."); return 1
    failed = 0
    for name, url, body in targets:
        req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"{name}: 보냄 ({resp.status})")
        except Exception as e:  # 네트워크·주소 오류는 알리고 계속
            failed += 1
            print(f"{name}: 실패 — {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
