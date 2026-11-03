#!/usr/bin/env python3
"""지표 계산기. 산출물에 적는 수치는 LLM이 추정하지 않고 이 스크립트로 계산한다 (AGENTS.md 8절, G-MEASURE).

사용:
  python3 automation/scripts/metrics.py sample-db 05.outputs/sample.sqlite            # 기본 스키마 + 가상 데이터 (시험용)
  python3 automation/scripts/metrics.py list                                           # automation/sql/ 템플릿 목록
  python3 automation/scripts/metrics.py run 진도율 --db 05.outputs/sample.sqlite --param from=2026-09-01 --param to=2026-09-30
  python3 automation/scripts/metrics.py run automation/sql/M01_x.sql --url "$DATABASE_URL"   # PostgreSQL은 psql 필요
  python3 automation/scripts/metrics.py effect-size --csv 결과.csv --group group --value score [--treat 실험]
  python3 automation/scripts/metrics.py compare --metric M-F71 --baseline 52 --target 24 --actual 31 [--lower-is-better]

run: SQL 안의 {{from}}·{{to}} 같은 자리를 --param으로 채운다. 결과는 화면에 표로, 그리고 05.outputs/metrics_<이름>_YYYYMMDD_HHMM.csv 로 저장한다.
기본 스키마(automation/sql/README.md)와 회사 DB가 다르면 같은 이름의 뷰를 만들거나 SQL을 복사해 고친다.
표준 라이브러리만 쓴다 (sqlite3 내장, PostgreSQL은 psql CLI 호출).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import math
import os
import random
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("EDPM_ROOT") or Path(__file__).resolve().parents[2])
SQL_DIR = ROOT / "automation" / "sql"
OUT_DIR = ROOT / "05.outputs"

SCHEMA = """
create table if not exists learners (learner_key text primary key, segment text, grade text, joined_at date);
create table if not exists enrollments (learner_key text, course_id text, enrolled_at date, expires_at date, completed_at date, price integer);
create table if not exists learning_events (
  event_time text, learner_key text, event text, course_id text, unit_id text, item_id text,
  value real, session_id text
);
create index if not exists ix_ev_time on learning_events(event_time);
create index if not exists ix_ev_learner on learning_events(learner_key, event);
"""


def resolve_sql(name: str) -> tuple[str, str]:
    p = Path(name)
    if not p.exists():
        cands = list(SQL_DIR.glob(f"*{name}*.sql"))
        if len(cands) != 1:
            sys.exit(f"SQL을 찾을 수 없거나 여러 개입니다: {name} → {[c.name for c in cands]}")
        p = cands[0]
    return p.stem, p.read_text(encoding="utf-8")


def fill_params(sql: str, params: dict) -> str:
    missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", sql)) - set(params))
    if missing:
        sys.exit(f"파라미터가 비었습니다: {missing} (--param 이름=값)")
    for k, v in params.items():
        sql = sql.replace("{{" + k + "}}", v)
    return sql


def run_sqlite(db: str, sql: str) -> tuple[list[str], list[list]]:
    con = sqlite3.connect(db)
    try:
        cur = con.execute(sql)
        cols = [c[0] for c in cur.description or []]
        rows = [list(r) for r in cur.fetchall()]
    finally:
        con.close()
    return cols, rows


def run_psql(url: str, sql: str) -> tuple[list[str], list[list]]:
    r = subprocess.run(["psql", url, "-v", "ON_ERROR_STOP=1", "--csv", "-c", sql], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"psql 실패: {r.stderr.strip()}")
    reader = csv.reader(io.StringIO(r.stdout))
    rows = list(reader)
    return (rows[0], rows[1:]) if rows else ([], [])


def table(cols: list[str], rows: list[list]) -> str:
    if not cols:
        return "(결과 없음)"
    fmt = lambda v: f"{v:.4g}" if isinstance(v, float) else ("" if v is None else str(v))  # noqa: E731
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows[:50]]
    if len(rows) > 50:
        out.append(f"... {len(rows)}행 중 50행")
    return "\n".join(out)


def cmd_run(a) -> None:
    name, sql = resolve_sql(a.sql)
    params = dict(p.split("=", 1) for p in a.param)
    sql = fill_params(sql, params)
    if a.url:
        cols, rows = run_psql(a.url, sql)
    else:
        if not a.db:
            sys.exit("--db <sqlite 파일> 또는 --url <postgres URL> 이 필요합니다")
        cols, rows = run_sqlite(a.db, sql)
    print(f"# {name}  ({'psql' if a.url else a.db}; " + ", ".join(f"{k}={v}" for k, v in params.items()) + ")\n")
    print(table(cols, rows))
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"metrics_{name}_{dt.datetime.now():%Y%m%d_%H%M}.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    print(f"\n저장: {out.relative_to(ROOT)}  (산출물에는 이 경로와 SQL 파일명을 적습니다)")


def cmd_list(a) -> None:
    for p in sorted(SQL_DIR.glob("*.sql")):
        head = next((l.lstrip("- ").strip() for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("--")), "")
        params = sorted(set(re.findall(r"\{\{(\w+)\}\}", p.read_text(encoding="utf-8"))))
        print(f"{p.stem:30s} {head}  파라미터: {', '.join(params) or '없음'}")


def cohens_d(x: list[float], y: list[float]) -> dict:
    nx, ny = len(x), len(y)
    mx, my = sum(x) / nx, sum(y) / ny
    vx = sum((v - mx) ** 2 for v in x) / (nx - 1) if nx > 1 else 0.0
    vy = sum((v - my) ** 2 for v in y) / (ny - 1) if ny > 1 else 0.0
    sp = math.sqrt(((nx - 1) * vx + (ny - 1) * vy) / max(nx + ny - 2, 1))
    d = (mx - my) / sp if sp else float("nan")
    se = math.sqrt((nx + ny) / (nx * ny) + d * d / (2 * (nx + ny))) if nx and ny and not math.isnan(d) else float("nan")
    level = "작음(<0.2)" if abs(d) < 0.2 else "작은 효과(0.2~0.5)" if abs(d) < 0.5 else "중간(0.5~0.8)" if abs(d) < 0.8 else "큼(≥0.8)"
    return {"n_treat": nx, "n_ctrl": ny, "mean_treat": mx, "mean_ctrl": my, "d": d, "ci95": (d - 1.96 * se, d + 1.96 * se), "level": level}


def cmd_effect(a) -> None:
    with open(a.csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    groups = sorted({r[a.group] for r in rows})
    if len(groups) != 2:
        sys.exit(f"집단이 2개여야 합니다: {groups}")
    treat = a.treat or groups[0]
    ctrl = [g for g in groups if g != treat][0]
    x = [float(r[a.value]) for r in rows if r[a.group] == treat and r[a.value] not in ("", None)]
    y = [float(r[a.value]) for r in rows if r[a.group] == ctrl and r[a.value] not in ("", None)]
    if not x or not y:
        sys.exit(f"값이 있는 표본이 두 집단 모두 필요합니다 ({treat}: {len(x)}건, {ctrl}: {len(y)}건).")
    res = cohens_d(x, y)
    print(f"# 효과크기 (Cohen's d, 합동 표준편차)\n")
    print(f"| 집단 | n | 평균 |\n|---|---|---|\n| {treat} (처치) | {res['n_treat']} | {res['mean_treat']:.3f} |\n| {ctrl} (비교) | {res['n_ctrl']} | {res['mean_ctrl']:.3f} |\n")
    print(f"d = {res['d']:.3f}  (95% CI {res['ci95'][0]:.3f} ~ {res['ci95'][1]:.3f}) → {res['level']}")
    if res['ci95'][0] <= 0 <= res['ci95'][1]:
        print("신뢰구간이 0을 포함합니다. 효과 방향을 단정하지 말고 표본·기간을 늘려 재측정하세요 ([[domain/효과크기와증거수준]]).")
    if min(res['n_treat'], res['n_ctrl']) < 30:
        print("표본이 30명 미만입니다. 증거 수준을 '탐색적'으로 적으세요.")


def cmd_compare(a) -> None:
    b, t, x = a.baseline, a.target, a.actual
    better = (x <= t) if a.lower_is_better else (x >= t)
    moved = (b - x) if a.lower_is_better else (x - b)
    span = abs(t - b) or 1e-9
    print(f"| 지표 | 기준선 | 목표 | 실제 | 변화 | 목표 달성 |\n|---|---|---|---|---|---|")
    print(f"| {a.metric} | {b:g} | {t:g} | {x:g} | {moved:+g} ({moved / span * 100:.0f}% of 목표 폭) | {'예' if better else '아니오'} |")


def cmd_sample(a) -> None:
    random.seed(7)
    p = Path(a.path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        p.unlink()
    con = sqlite3.connect(p)
    con.executescript(SCHEMA)
    start = dt.date(2026, 9, 1)
    for i in range(200):
        lk = f"L{i:04d}"
        seg = random.choice(["중1", "중2", "중3"])
        joined = start + dt.timedelta(days=random.randint(0, 40))
        con.execute("insert into learners values (?,?,?,?)", (lk, "학원", seg, joined.isoformat()))
        done = random.random() < 0.35
        con.execute("insert into enrollments values (?,?,?,?,?,?)",
                    (lk, "C-MATH-1", joined.isoformat(), (joined + dt.timedelta(days=90)).isoformat(),
                     (joined + dt.timedelta(days=random.randint(20, 60))).isoformat() if done else None, 49000))
        active_weeks = random.choice([1, 2, 3, 4, 6, 8, 10])
        for w in range(active_weeks):
            for _ in range(random.randint(1, 5)):
                day = joined + dt.timedelta(days=w * 7 + random.randint(0, 6))
                unit = f"U{random.randint(1, 12):02d}"
                con.execute("insert into learning_events values (?,?,?,?,?,?,?,?)",
                            (f"{day}T{random.randint(15, 22):02d}:00:00", lk, "lesson_completed", "C-MATH-1", unit, None, 1, f"s{i}{w}"))
                for k in range(random.randint(2, 6)):
                    con.execute("insert into learning_events values (?,?,?,?,?,?,?,?)",
                                (f"{day}T{random.randint(15, 22):02d}:10:00", lk, "attempt_submitted", "C-MATH-1", unit, f"I{unit}{k}",
                                 1 if random.random() < 0.65 else 0, f"s{i}{w}"))
            if random.random() < 0.6:
                con.execute("insert into learning_events values (?,?,?,?,?,?,?,?)",
                            (f"{joined + dt.timedelta(days=w * 7 + 5)}T20:00:00", lk, "assignment_submitted", "C-MATH-1", f"A{w}", None, 1, None))
    con.commit(); con.close()
    print(f"가상 데이터 생성: {p} (학습자 200, 과정 1, 12단원). 실제 학습자 데이터가 아닙니다.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("run"); s.add_argument("sql"); s.add_argument("--db"); s.add_argument("--url"); s.add_argument("--param", action="append", default=[])
    sub.add_parser("list")
    s = sub.add_parser("effect-size"); s.add_argument("--csv", required=True); s.add_argument("--group", required=True); s.add_argument("--value", required=True); s.add_argument("--treat")
    s = sub.add_parser("compare"); s.add_argument("--metric", required=True)
    for k in ("baseline", "target", "actual"):
        s.add_argument(f"--{k}", type=float, required=True)
    s.add_argument("--lower-is-better", action="store_true")
    s = sub.add_parser("sample-db"); s.add_argument("path")
    a = ap.parse_args()
    {"run": cmd_run, "list": cmd_list, "effect-size": cmd_effect, "compare": cmd_compare, "sample-db": cmd_sample}[a.cmd](a)


if __name__ == "__main__":
    main()
