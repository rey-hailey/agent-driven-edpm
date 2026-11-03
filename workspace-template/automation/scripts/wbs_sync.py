#!/usr/bin/env python3
"""M02 WBS(CSV)를 일정 관리 도구와 동기화한다. 기본 도구는 GitHub(Issues·Milestones·Projects).

원칙: 계획 필드(이름·단계·산출물·공수·시작·종료·선행·학사제약)는 CSV가 정본,
진행 필드(상태)는 도구가 정본이다. push는 계획을 도구로 보내고, pull은 상태를 CSV로 가져온다.

사용:
  python3 automation/scripts/wbs_sync.py status                 # 진행 요약 (도구 없이 CSV만)
  python3 automation/scripts/wbs_sync.py setup  [--dry-run]     # GitHub 라벨·마일스톤 준비
  python3 automation/scripts/wbs_sync.py push   [--dry-run]     # WP → GitHub 이슈 생성·갱신, 이슈 번호를 CSV에 기록
  python3 automation/scripts/wbs_sync.py pull   [--dry-run]     # GitHub 이슈 상태 → CSV 상태 열
  python3 automation/scripts/wbs_sync.py export --to jira|linear|notion|sheets
                                                               # 가져오기용 CSV를 05.outputs/에 생성

설정: automation/wbs.json (tool, repo, project, project_owner, assignees). 옵션 --repo, --project로 덮어쓸 수 있다.
GitHub 사용 전: gh CLI 설치, `gh auth login` (Projects를 쓰면 `gh auth refresh -s project`).
표준 라이브러리만 쓴다. 테스트용으로 GH_BIN 환경변수로 gh 실행 파일을 바꿀 수 있다.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "automation" / "wbs.json"
DEFAULT_CSV = "03.docs/M.관리/M02_WBS.csv"
ISSUE_COL = "이슈"
STATUSES = ("예정", "진행", "완료", "지연")
STAGE_COLORS = {"발견": "c5def5", "정의": "bfd4f2", "설계": "d4c5f9", "구축": "f9d0c4",
                "검증": "fef2c0", "출시": "c2e0c6", "측정": "e6e6e6", "관리": "ededed", "사업": "fbca04"}
STATUS_LABEL = {"진행": ("상태:진행", "0e8a16"), "지연": ("상태:지연", "d93f0b")}
TITLE_RE = re.compile(r"^\[(WP-[\w.]+)\]")


# ---------- 공통 ----------

def load_config(args) -> dict:
    cfg = {"tool": "github", "repo": "", "project": None, "project_owner": "", "csv": DEFAULT_CSV, "assignees": {}}
    if CONFIG.exists():
        cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    if getattr(args, "repo", None):
        cfg["repo"] = args.repo
    if getattr(args, "project", None):
        cfg["project"] = args.project
    if getattr(args, "csv", None):
        cfg["csv"] = args.csv
    return cfg


def read_wbs(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        fields = list(r.fieldnames or [])
        rows = [dict(row) for row in r]
    if ISSUE_COL not in fields:
        fields.append(ISSUE_COL)
        for row in rows:
            row[ISSUE_COL] = ""
    return fields, rows


def write_wbs(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def is_example(row: dict) -> bool:
    return (row.get("이름") or "").startswith("(예시)")


def real_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("wp_id") and not is_example(r)]


def parse_date(s: str | None) -> dt.date | None:
    try:
        return dt.date.fromisoformat((s or "").strip())
    except ValueError:
        return None


def gh(*args: str, dry: bool = False, mutate: bool = False) -> str:
    cmd = [os.environ.get("GH_BIN", "gh"), *args]
    if dry and mutate:
        print("  (dry-run) " + " ".join(cmd))
        return ""
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"gh 실패: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def need_repo(cfg: dict) -> str:
    if not cfg.get("repo"):
        sys.exit("GitHub 저장소가 없습니다. automation/wbs.json의 repo에 owner/name을 적거나 --repo를 주세요.")
    return cfg["repo"]


# ---------- status ----------

def cmd_status(cfg: dict, args) -> None:
    _, rows = read_wbs(ROOT / cfg["csv"])
    rows = real_rows(rows)
    today = parse_date(args.today) or dt.date.today()
    week_end = today + dt.timedelta(days=7)
    count = {s: 0 for s in STATUSES}
    overdue, due_soon = [], []
    for r in rows:
        st = r.get("상태") or "예정"
        count[st] = count.get(st, 0) + 1
        end = parse_date(r.get("종료"))
        if st != "완료" and end and end < today:
            overdue.append(r)
        elif st != "완료" and end and today <= end <= week_end:
            due_soon.append(r)
    total = len(rows) or 1
    print(f"# WBS 진행 요약 ({today})\n")
    print("| 전체 | " + " | ".join(count) + " | 완료율 |")
    print("|" + "---|" * (len(count) + 2))
    print(f"| {len(rows)} | " + " | ".join(str(v) for v in count.values()) + f" | {count.get('완료', 0) * 100 // total}% |")
    for title, items in (("종료일 지난 미완료 WP", overdue), ("7일 안에 끝나야 하는 WP", due_soon)):
        print(f"\n## {title} ({len(items)})")
        for r in items:
            issue = f" #{r[ISSUE_COL]}" if r.get(ISSUE_COL) else ""
            print(f"- {r['wp_id']} {r.get('이름', '')} — 종료 {r.get('종료', '')}, 담당 {r.get('담당', '')}, 상태 {r.get('상태', '')}{issue}")


# ---------- GitHub ----------

def issue_body(r: dict) -> str:
    keys = ["wp_id", "단계", "산출물ID", "담당", "공수(일)", "시작", "종료", "선행", "학사제약"]
    lines = ["| 항목 | 값 |", "|---|---|"] + [f"| {k} | {r.get(k) or ''} |" for k in keys]
    return ("\n".join(lines) + "\n\n> EdPM WBS(`03.docs/M.관리/M02_WBS.csv`)에서 생성. "
            "계획 필드는 CSV에서 고치고 `wbs_sync.py push`로 반영합니다. 진행 상태는 이 이슈에서 바꿉니다 "
            "(닫기 = 완료, 라벨 `상태:진행`·`상태:지연`).\n")


def labels_for(r: dict) -> list[str]:
    out = ["wp"]
    if r.get("단계"):
        out.append(f"단계:{r['단계']}")
    for d in (r.get("산출물ID") or "").split(";"):
        if d.strip():
            out.append(f"산출물:{d.strip()}")
    if r.get("상태") in STATUS_LABEL:
        out.append(STATUS_LABEL[r["상태"]][0])
    return out


def list_issues(repo: str) -> dict[int, dict]:
    out = gh("issue", "list", "-R", repo, "--label", "wp", "--state", "all", "--limit", "1000",
             "--json", "number,state,title,body,labels,assignees,milestone,url")
    return {i["number"]: i for i in json.loads(out or "[]")}


def ensure_labels_milestones(repo: str, rows: list[dict], dry: bool) -> None:
    labels = {"wp": ("1d76db", "EdPM WBS 작업 패키지")}
    for name, color in STATUS_LABEL.values():
        labels[name] = (color, "EdPM WBS 진행 상태")
    for r in rows:
        if r.get("단계"):
            labels[f"단계:{r['단계']}"] = (STAGE_COLORS.get(r["단계"], "ededed"), "EdPM WBS 단계")
        for d in (r.get("산출물ID") or "").split(";"):
            if d.strip():
                labels[f"산출물:{d.strip()}"] = ("ffffff", "EdPM 산출물 ID")
    for name, (color, desc) in labels.items():
        gh("label", "create", name, "-R", repo, "--color", color, "--description", desc, "--force", dry=dry, mutate=True)

    due: dict[str, dt.date | None] = {}
    for r in rows:
        if r.get("단계"):
            end = parse_date(r.get("종료"))
            cur = due.get(r["단계"])
            due[r["단계"]] = max(filter(None, [cur, end]), default=None)
    existing = {m["title"]: m for m in json.loads(gh("api", f"repos/{repo}/milestones?state=all&per_page=100") or "[]")}
    for stage, d in due.items():
        fields = ["-f", f"title={stage}", "-f", "description=EdPM WBS 단계"]
        if d:
            fields += ["-f", f"due_on={d.isoformat()}T23:59:59Z"]
        if stage in existing:
            gh("api", "-X", "PATCH", f"repos/{repo}/milestones/{existing[stage]['number']}", *fields, dry=dry, mutate=True)
        else:
            gh("api", "-X", "POST", f"repos/{repo}/milestones", *fields, dry=dry, mutate=True)


def project_ctx(cfg: dict, repo: str) -> dict | None:
    num = cfg.get("project")
    if not num:
        return None
    owner = cfg.get("project_owner") or repo.split("/")[0]
    view = json.loads(gh("project", "view", str(num), "--owner", owner, "--format", "json"))
    fields = json.loads(gh("project", "field-list", str(num), "--owner", owner, "--format", "json")).get("fields", [])
    pick = lambda names: next((f["id"] for f in fields if f.get("name") in names), None)  # noqa: E731
    items = json.loads(gh("project", "item-list", str(num), "--owner", owner, "--format", "json", "--limit", "1000")).get("items", [])
    by_issue = {it["content"]["number"]: it["id"] for it in items if (it.get("content") or {}).get("number")}
    return {"num": str(num), "owner": owner, "id": view["id"], "items": by_issue,
            "start": pick({"시작", "Start", "Start date"}), "end": pick({"종료", "End", "Target date", "Due"})}


def sync_project(ctx: dict, number: int, url: str, r: dict, dry: bool) -> None:
    item = ctx["items"].get(number)
    if not item:
        out = gh("project", "item-add", ctx["num"], "--owner", ctx["owner"], "--url", url, "--format", "json", dry=dry, mutate=True)
        if dry:
            return
        item = json.loads(out)["id"]
        ctx["items"][number] = item
    for key, col in (("start", "시작"), ("end", "종료")):
        if ctx[key] and parse_date(r.get(col)):
            gh("project", "item-edit", "--id", item, "--project-id", ctx["id"], "--field-id", ctx[key],
               "--date", r[col], dry=dry, mutate=True)


def cmd_setup(cfg: dict, args) -> None:
    repo = need_repo(cfg)
    _, rows = read_wbs(ROOT / cfg["csv"])
    ensure_labels_milestones(repo, real_rows(rows), args.dry_run)
    print(f"라벨·마일스톤 준비 완료: {repo}")


def cmd_push(cfg: dict, args) -> None:
    repo = need_repo(cfg)
    path = ROOT / cfg["csv"]
    fields, rows = read_wbs(path)
    todo = real_rows(rows)
    skipped = len([r for r in rows if is_example(r)])
    if skipped:
        print(f"(예시) 행 {skipped}개는 건너뜁니다. 실제 계획을 쓰면 예시 행을 지우세요.")
    if not todo:
        sys.exit("보낼 WP가 없습니다.")
    ensure_labels_milestones(repo, todo, args.dry_run)
    issues = list_issues(repo)
    by_wp = {m.group(1): n for n, i in issues.items() if (m := TITLE_RE.match(i["title"]))}
    ctx = project_ctx(cfg, repo)
    created = updated = unchanged = 0
    for r in todo:
        title = f"[{r['wp_id']}] {r.get('이름', '')}"
        body = issue_body(r)
        labels = labels_for(r)
        num = int(r[ISSUE_COL]) if (r.get(ISSUE_COL) or "").isdigit() else by_wp.get(r["wp_id"])
        assignee = cfg.get("assignees", {}).get(r.get("담당") or "")
        if num and num in issues:
            cur = issues[num]
            cur_labels = {lb["name"] for lb in cur.get("labels", [])}
            stale = [lb for lb in cur_labels if lb.startswith("상태:") and lb not in labels]
            changed = (cur["title"] != title or (cur.get("body") or "").strip() != body.strip()
                       or not set(labels) <= cur_labels or stale
                       or ((cur.get("milestone") or {}).get("title") != r.get("단계")))
            if changed:
                extra = ["--add-label", ",".join(labels)]
                if stale:
                    extra += ["--remove-label", ",".join(stale)]
                if r.get("단계"):
                    extra += ["--milestone", r["단계"]]
                gh("issue", "edit", str(num), "-R", repo, "--title", title, "--body", body, *extra, dry=args.dry_run, mutate=True)
                updated += 1
            else:
                unchanged += 1
            want_closed = r.get("상태") == "완료"
            if want_closed and cur["state"] == "OPEN":
                gh("issue", "close", str(num), "-R", repo, dry=args.dry_run, mutate=True)
            elif not want_closed and cur["state"] == "CLOSED" and args.reopen:
                gh("issue", "reopen", str(num), "-R", repo, dry=args.dry_run, mutate=True)
            url = cur["url"]
        else:
            extra = ["--label", ",".join(labels)]
            if r.get("단계"):
                extra += ["--milestone", r["단계"]]
            if assignee:
                extra += ["--assignee", assignee]
            out = gh("issue", "create", "-R", repo, "--title", title, "--body", body, *extra, dry=args.dry_run, mutate=True)
            created += 1
            if args.dry_run:
                continue
            url = out.strip().splitlines()[-1]
            num = int(url.rstrip("/").rsplit("/", 1)[-1])
            if r.get("상태") == "완료":
                gh("issue", "close", str(num), "-R", repo, mutate=True)
        r[ISSUE_COL] = str(num)
        if ctx:
            sync_project(ctx, num, url, r, args.dry_run)
    if not args.dry_run:
        write_wbs(path, fields, rows)
    print(f"push {repo}: 생성 {created}, 갱신 {updated}, 변경 없음 {unchanged}" + (" (dry-run, CSV 미변경)" if args.dry_run else ""))


def cmd_pull(cfg: dict, args) -> None:
    repo = need_repo(cfg)
    path = ROOT / cfg["csv"]
    fields, rows = read_wbs(path)
    issues = list_issues(repo)
    by_wp = {m.group(1): n for n, i in issues.items() if (m := TITLE_RE.match(i["title"]))}
    changes, known = [], set()
    for r in real_rows(rows):
        num = int(r[ISSUE_COL]) if (r.get(ISSUE_COL) or "").isdigit() else by_wp.get(r["wp_id"])
        if not num or num not in issues:
            continue
        known.add(num)
        i = issues[num]
        names = {lb["name"] for lb in i.get("labels", [])}
        old = r.get("상태") or "예정"
        if i["state"] == "CLOSED":
            new = "완료"
        elif "상태:지연" in names:
            new = "지연"
        elif "상태:진행" in names or old == "완료":
            new = "진행"
        else:
            new = old
        if new != old:
            changes.append((r["wp_id"], old, new, num))
            r["상태"] = new
        r[ISSUE_COL] = str(num)
    for wp, old, new, num in changes:
        print(f"- {wp} #{num}: {old} → {new}")
    others = [i for n, i in issues.items() if n not in known]
    if others:
        print(f"\nCSV에 없는 wp 이슈 {len(others)}건 (팀이 GitHub에서 만든 작업일 수 있음, CSV에 추가할지 PM이 판단):")
        for i in others:
            print(f"- #{i['number']} {i['title']}")
    if not args.dry_run:
        write_wbs(path, fields, rows)
    print(f"\npull {repo}: 상태 변경 {len(changes)}건" + (" (dry-run, CSV 미변경)" if args.dry_run else ""))


# ---------- export ----------

EXPORTS = {
    # 도구별 가져오기 화면에서 열을 다시 매핑할 수 있다. 날짜는 YYYY-MM-DD.
    "jira": [("Summary", lambda r: f"[{r['wp_id']}] {r.get('이름', '')}"), ("Issue Type", lambda r: "Task"),
             ("Description", lambda r: f"단계 {r.get('단계', '')} / 산출물 {r.get('산출물ID', '')} / 선행 {r.get('선행', '')} / 학사제약 {r.get('학사제약', '')}"),
             ("Labels", lambda r: f"wp {r.get('단계', '')}".strip()), ("Start date", lambda r: r.get("시작", "")),
             ("Due date", lambda r: r.get("종료", "")), ("Original Estimate", lambda r: f"{r.get('공수(일)', '')}d" if r.get("공수(일)") else ""),
             ("Assignee", lambda r: r.get("담당", "")), ("Status", lambda r: r.get("상태", "")), ("External ID", lambda r: r["wp_id"])],
    "linear": [("Title", lambda r: f"[{r['wp_id']}] {r.get('이름', '')}"),
               ("Description", lambda r: f"단계 {r.get('단계', '')} / 산출물 {r.get('산출물ID', '')} / 선행 {r.get('선행', '')} / 학사제약 {r.get('학사제약', '')}"),
               ("Status", lambda r: {"예정": "Todo", "진행": "In Progress", "완료": "Done", "지연": "In Progress"}.get(r.get("상태", ""), "Todo")),
               ("Labels", lambda r: f"wp,{r.get('단계', '')}"), ("Estimate", lambda r: r.get("공수(일)", "")),
               ("Due Date", lambda r: r.get("종료", "")), ("Assignee", lambda r: r.get("담당", ""))],
    "notion": [("이름", lambda r: f"[{r['wp_id']}] {r.get('이름', '')}"), ("WP", lambda r: r["wp_id"]), ("단계", lambda r: r.get("단계", "")),
               ("산출물", lambda r: r.get("산출물ID", "")), ("담당", lambda r: r.get("담당", "")), ("공수(일)", lambda r: r.get("공수(일)", "")),
               ("시작", lambda r: r.get("시작", "")), ("종료", lambda r: r.get("종료", "")), ("선행", lambda r: r.get("선행", "")),
               ("학사제약", lambda r: r.get("학사제약", "")), ("상태", lambda r: r.get("상태", ""))],
}


def cmd_export(cfg: dict, args) -> None:
    fields, rows = read_wbs(ROOT / cfg["csv"])
    rows = real_rows(rows)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    out = ROOT / "05.outputs" / f"wbs_{args.to}_{stamp}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    # 엑셀에서 한글이 깨지지 않도록 BOM을 붙인다 (Notion·Jira·Linear·Google Sheets도 읽는다)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if args.to == "sheets":
            w.writerow(fields)
            w.writerows([[r.get(k, "") for k in fields] for r in rows])
        else:
            spec = EXPORTS[args.to]
            w.writerow([h for h, _ in spec])
            w.writerows([[fn(r) for _, fn in spec] for r in rows])
    print(f"{out.relative_to(ROOT)} ({len(rows)}행)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--csv", help=f"WBS CSV 경로 (기본 {DEFAULT_CSV})")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--today", help="기준일 YYYY-MM-DD (기본 오늘)")
    for name in ("setup", "push", "pull"):
        s = sub.add_parser(name)
        s.add_argument("--repo", help="owner/name (기본 automation/wbs.json)")
        s.add_argument("--project", type=int, help="GitHub Projects 번호 (선택)")
        s.add_argument("--dry-run", action="store_true", help="실행할 gh 명령만 보여주고 바꾸지 않음")
        if name == "push":
            s.add_argument("--reopen", action="store_true", help="CSV가 미완료인데 닫힌 이슈를 다시 연다 (기본은 GitHub 상태 유지)")
    s = sub.add_parser("export")
    s.add_argument("--to", required=True, choices=["jira", "linear", "notion", "sheets"])
    args = p.parse_args()
    cfg = load_config(args)
    {"status": cmd_status, "setup": cmd_setup, "push": cmd_push, "pull": cmd_pull, "export": cmd_export}[args.cmd](cfg, args)


if __name__ == "__main__":
    main()
