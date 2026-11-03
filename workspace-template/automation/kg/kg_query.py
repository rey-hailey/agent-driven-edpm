#!/usr/bin/env python3
"""교육과정 지식그래프 조회 (/edpm-curriculum)

data/curriculum-kg/kg.db (kg_build.py 결과)를 읽어 PM이 자주 묻는 질문에 마크다운으로 답한다.

명령:
  stats                                   데이터 규모·버전·연결 점검
  search <키워드...> [--level --course --grade --limit]
                                          성취기준 찾기 (요약·코드·영역·과목)
  standard <코드>                          성취기준 상세: 토픽, 평가 증거, 오개념, 앞뒤 선수 관계, 전환기 정보
  path <코드> [--up|--down] [--layer official|all] [--depth N]
                                          선수학습 경로 (공식 관계 기본, 후보는 '권장 순서'로 표시)
  seed <코드> [--all]                      문항·콘텐츠 제작 씨앗 (평가 증거, 평가 예시, 오개념)
  align <설명 문장> [--level --course --grade --limit]
                                          우리 콘텐츠·기능 설명에 맞는 성취기준 후보 (사람이 최종 판단)
  coverage <매핑 CSV> [--level --course --grade]
                                          커버리지: 다룬/안 다룬 성취기준, 빠진 선수 성취기준
  gaps [--transition e2m|m2h] [--subject 과목] [--top N]
                                          전환기 격차 순위, 과목별 신규 개념·쉬운 설명·연계 근거
  courses [--level middle|high] [--category ...]
                                          과목 목록과 고교 과목 간 권장 순서
  export (--map <CSV> | --codes 코드,코드) 제안서·산출물용 성취기준 정합표 (출처 고지 포함)

공통: --db <경로>, --out <파일> (지정하면 파일로 저장)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEVEL_KO = {"elementary": "초", "middle": "중", "high": "고", "vocational": "고(직업)"}
SET_KO = {"elementary": "초등 내", "middle": "중학교 내", "high": "고교 내", "vocational": "직업계 내",
          "elementary->middle": "초→중 연결", "middle->high": "중→고 연결"}


def norm_code(code: str) -> str:
    return re.sub(r"[\[\]\s]", "", code).replace("Ⅰ", "I").replace("Ⅱ", "II")


class KG:
    def __init__(self, path: Path):
        if not path.exists():
            sys.exit(f"지식그래프가 없습니다: {path}\n먼저 automation/kg/kg_sync.sh 와 kg_build.py 를 실행하세요.")
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row

    def q(self, sql, *args):
        return self.db.execute(sql, args).fetchall()

    def meta(self, key):
        r = self.q("select value from meta where key=?", key)
        return r[0][0] if r else None

    def find_standard(self, code: str):
        rows = self.q("select * from standard where code_norm=?", norm_code(code))
        if not rows:
            rows = self.q("select * from standard where id=?", code)
        return rows

    def topics_of(self, std_id: str, include_aux=True):
        rows = self.q("""select t.*, a.kind as align_kind, a.confidence from alignment a join topic t on t.id=a.topic_id
                         where a.standard_id=? order by case t.topic_role when 'anchor' then 0 when 'facet' then 1 else 2 end""", std_id)
        return [r for r in rows if include_aux or r["topic_role"] != "auxiliary"]

    def standards_of_topic(self, topic_id: str):
        return self.q("""select s.* from alignment a join standard s on s.id=a.standard_id where a.topic_id=?
                         order by case a.kind when 'assesses' then 0 else 1 end""", topic_id)

    def neighbor_standards(self, std_id: str, direction: str, layer: str):
        """direction up: 이 성취기준의 선수 성취기준 / down: 이 성취기준 다음 성취기준"""
        tids = [t["id"] for t in self.topics_of(std_id)]
        if not tids:
            return []
        ph = ",".join("?" * len(tids))
        mine, other = ("dependent_id", "prereq_id") if direction == "up" else ("prereq_id", "dependent_id")
        layer_sql = "" if layer == "all" else "and e.layer='official'"
        edges = self.q(f"select * from edge e where e.{mine} in ({ph}) {layer_sql}", *tids)
        out = {}
        for e in edges:
            for s in self.standards_of_topic(e[other])[:1]:
                if s["id"] == std_id:
                    continue
                cur = out.get(s["id"])
                if cur is None or (cur[1]["layer"] != "official" and e["layer"] == "official"):
                    out[s["id"]] = (s, e)
        return list(out.values())

    def gap_concept(self, code_norm: str):
        return self.q("select * from gap_new_concept where code_norm=?", code_norm)


def std_line(s) -> str:
    grade = s["grade_band"] or ""
    return f"`{s['code']}` {s['summary']} ({LEVEL_KO.get(s['level'], s['level'])} {s['course_label'] or ''} {grade} / {s['domain_label'] or ''})".replace("  ", " ")


def locator(s) -> str:
    parts = [s["source_id"] or ""]
    if s["printed_page"]:
        parts.append(f"p.{s['printed_page']}")
    elif s["section"]:
        parts.append(s["section"])
    return " ".join(p for p in parts if p)


def footer(kg: KG) -> str:
    return ("\n---\n" + (kg.meta("attribution") or "") +
            " 후보(candidate) 관계는 저장소가 제안한 권장 순서이며 공식 선수 관계가 아니다. "
            "평가 증거·평가 예시·오개념은 검토 전 초안(source-grounded-draft)이므로 교사·교과 전문가 검토 후 사용한다.\n")


def filt(args, alias="s"):
    cond, vals = [], []
    if getattr(args, "level", None):
        cond.append(f"{alias}.level=?"); vals.append(args.level)
    if getattr(args, "course", None):
        cond.append(f"{alias}.course_label like ?"); vals.append(f"%{args.course}%")
    if getattr(args, "grade", None):
        cond.append(f"{alias}.grade_band=?"); vals.append(args.grade)
    return cond, vals


# ---------- commands ----------

def cmd_stats(kg: KG, args) -> str:
    o = ["# 교육과정 지식그래프 현황", "", "| 원천 | 프로필 | 릴리스 | 커밋 |", "|------|--------|--------|------|"]
    for r in kg.q("select * from release"):
        o.append(f"| {r['repo']} | {r['profile']} | {r['release_id']} | {(r['commit_sha'] or '')[:10]} |")
    o += ["", "| 항목 | 수 |", "|------|----|"]
    for r in kg.q("select level, count(*) n from standard group by level"):
        o.append(f"| 성취기준 ({LEVEL_KO.get(r['level'])}) | {r['n']} |")
    for r in kg.q("select level, count(*) n from topic group by level"):
        o.append(f"| 세부 토픽 ({LEVEL_KO.get(r['level'])}) | {r['n']} |")
    for r in kg.q("select edge_set, layer, count(*) n from edge group by 1,2 order by 1,2"):
        o.append(f"| 관계 {SET_KO.get(r['edge_set'], r['edge_set'])} [{r['layer']}] | {r['n']} |")
    o.append(f"| 전환기 격차 프로필 | {kg.q('select count(*) from gap_profile')[0][0]} |")
    o.append(f"| 전환기 신규 성취기준 | {kg.q('select count(*) from gap_new_concept')[0][0]} |")
    o += ["", f"연결 점검: `{kg.meta('join_check')}`", f"쉬운 설명 검토 상태: {kg.meta('easy_labels_review')}"]
    return "\n".join(o) + footer(kg)


def cmd_search(kg: KG, args) -> str:
    words = [w for w in args.words if w]
    cond, vals = filt(args)
    for w in words:
        cond.append("(s.summary like ? or s.code_norm like ? or s.domain_label like ? or s.course_label like ?)")
        vals += [f"%{w}%", f"%{norm_code(w)}%", f"%{w}%", f"%{w}%"]
    where = ("where " + " and ".join(cond)) if cond else ""
    rows = kg.q(f"select * from standard s {where} order by level, course_label, code_norm limit ?", *vals, args.limit)
    o = [f"# 성취기준 검색: {' '.join(words)}", "", f"{len(rows)}건 (최대 {args.limit})", "",
         "| 코드 | 학교급 | 과목 | 학년(군) | 영역 | 요약 |", "|------|--------|------|----------|------|------|"]
    for s in rows:
        o.append(f"| `{s['code']}` | {LEVEL_KO.get(s['level'])} | {s['course_label']} | {s['grade_band'] or '-'} | {s['domain_label'] or ''} | {s['summary']} |")
    return "\n".join(o) + footer(kg)


def cmd_standard(kg: KG, args) -> str:
    rows = kg.find_standard(args.code)
    if not rows:
        return f"`{args.code}`에 해당하는 성취기준이 없습니다. `search`로 찾아보세요."
    o = []
    for s in rows:
        o += [f"# {s['code']} {s['summary']}", "", "| 항목 | 값 |", "|------|----|",
              f"| 학교급·과목 | {LEVEL_KO.get(s['level'])} {s['course_label']} |",
              f"| 학년(군) | {s['grade_band'] or '미지정(고교 과목)'} |",
              f"| 영역 | {s['domain_label'] or ''} |",
              f"| 근거 위치 | {locator(s)} |",
              f"| 검증 상태 | {s['verification_status'] or ''} / {s['review_status'] or ''} |",
              f"| KG ID | `{s['id']}` |"]
        gc = kg.gap_concept(s["code_norm"])
        if gc:
            g = gc[0]
            o += [f"| 전환기 | **{ '초→중' if g['transition']=='e2m' else '중→고' } 신규 도입** ({g['subject']}). 쉬운 설명: {g['easy_label'] or '-'} — {g['easy_explain'] or ''} (AI 초안) |"]
        o += ["", "## 세부 토픽", "", "| 역할 | 정렬 | 유형 | 토픽 |", "|------|------|------|------|"]
        for t in kg.topics_of(s["id"]):
            o.append(f"| {t['topic_role']} | {t['align_kind']} | {t['facet_key'] or t['types'] or ''} | {t['label']} |")
        for direction, title in (("up", "먼저 배워야 하는 성취기준 (선수)"), ("down", "이어서 배우는 성취기준 (후속)")):
            nb = kg.neighbor_standards(s["id"], direction, "all")
            o += ["", f"## {title}", ""]
            if not nb:
                o.append("- 기록된 관계 없음 (공식 문서가 관계를 명시하지 않은 경우가 많음)")
            for ns, e in sorted(nb, key=lambda x: (x[1]["layer"] != "official", x[0]["code_norm"])):
                tag = "공식" if e["layer"] == "official" else "권장 순서(후보)"
                o.append(f"- [{tag}·{SET_KO.get(e['edge_set'], e['edge_set'])}] {std_line(ns)} — {e['basis'] or ''}")
    return "\n".join(o) + footer(kg)


def cmd_path(kg: KG, args) -> str:
    rows = kg.find_standard(args.code)
    if not rows:
        return f"`{args.code}`에 해당하는 성취기준이 없습니다."
    s0 = rows[0]
    direction = "down" if args.down else "up"
    o = [f"# 선수학습 경로 ({'후속' if direction=='down' else '선수'}, {'공식만' if args.layer=='official' else '공식+권장 순서'}, 깊이 {args.depth})",
         "", f"시작: {std_line(s0)}", ""]
    seen = {s0["id"]}

    def walk(sid, depth):
        if depth > args.depth:
            return
        for ns, e in sorted(kg.neighbor_standards(sid, direction, args.layer), key=lambda x: x[0]["code_norm"]):
            mark = "" if e["layer"] == "official" else " (권장 순서)"
            again = " (앞에서 나옴)" if ns["id"] in seen else ""
            o.append("  " * (depth - 1) + f"- {std_line(ns)}{mark}{again} — {SET_KO.get(e['edge_set'], e['edge_set'])}")
            if ns["id"] not in seen:
                seen.add(ns["id"])
                walk(ns["id"], depth + 1)

    walk(s0["id"], 1)
    if len(o) == 4:
        o.append("- 기록된 관계 없음. `--layer all`로 권장 순서까지 보거나, 공식 문서가 관계를 명시하지 않았을 수 있습니다.")
    return "\n".join(o) + footer(kg)


def cmd_seed(kg: KG, args) -> str:
    rows = kg.find_standard(args.code)
    if not rows:
        return f"`{args.code}`에 해당하는 성취기준이 없습니다."
    s = rows[0]
    o = [f"# 문항·콘텐츠 씨앗: {s['code']}", "", std_line(s), "",
         "> 아래 내용은 공식 해설을 바탕으로 저장소가 쓴 검토 전 초안입니다. 그대로 학생에게 내보내지 말고 교과 전문가 검토(E11 검수 절차)를 거칩니다.", ""]
    for t in kg.topics_of(s["id"], include_aux=args.all):
        ev, pr, mc = json.loads(t["evidence"] or "[]"), json.loads(t["assessment_prompts"] or "[]"), json.loads(t["misconceptions"] or "[]")
        if not (ev or pr or mc):
            continue
        o += [f"## {t['label']}", f"역할: {t['topic_role']} / 관점: {t['facet_key'] or ''} / 내용 상태: {t['content_kind']}", ""]
        if ev:
            o += ["**달성 증거 (관찰 가능한 행동)**"] + [f"- {x}" for x in ev] + [""]
        if pr:
            o += ["**평가 예시**"] + [f"- {x}" for x in pr] + [""]
        if mc:
            o += ["**흔한 오개념 (오답 선지·힌트 소재)**"] + [f"- {x}" for x in mc] + [""]
    if len(o) == 6:
        o.append("이 성취기준에는 평가 증거·오개념 초안이 없습니다 (고교 일반 과목은 템플릿 수준).")
    return "\n".join(o) + footer(kg)


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", text) if w not in {"학생", "학습", "이해", "하기", "있다", "한다"}]


def cmd_align(kg: KG, args) -> str:
    toks = tokens(" ".join(args.text))
    cond, vals = filt(args)
    where = ("where " + " and ".join(cond)) if cond else ""
    scored = []
    for s in kg.q(f"select * from standard s {where}", *vals):
        hay = f"{s['summary']} {s['domain_label']} {s['course_label']}"
        topic_txt = " ".join(t["label"] or "" for t in kg.topics_of(s["id"], include_aux=False)[:4])
        score = sum(2 if w in hay else (1 if w in topic_txt else 0) for w in toks)
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: (-x[0], x[1]["code_norm"]))
    o = [f"# 성취기준 정렬 후보: {' '.join(args.text)}", "", f"검색어: {', '.join(toks)}", "",
         "> 키워드 일치 점수로 고른 후보입니다. 최종 매핑은 사람이 판단하고 `E11_교육과정매핑.csv`에 관계(assesses/supports/extends/introduces)와 함께 적습니다.", "",
         "| 점수 | 코드 | 학교급·과목 | 학년(군) | 요약 |", "|------|------|-------------|----------|------|"]
    for sc, s in scored[: args.limit]:
        o.append(f"| {sc} | `{s['code']}` | {LEVEL_KO.get(s['level'])} {s['course_label']} | {s['grade_band'] or '-'} | {s['summary']} |")
    return "\n".join(o) + footer(kg)


def read_map(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f)]
    return [r for r in rows if (r.get("성취기준코드") or "").strip() and not (r.get("비고") or "").startswith("예시")] or rows


def cmd_coverage(kg: KG, args) -> str:
    mrows = read_map(args.map)
    covered = {norm_code(r["성취기준코드"]) for r in mrows if (r.get("성취기준코드") or "").strip()}
    cond, vals = filt(args)
    where = ("where " + " and ".join(cond)) if cond else ""
    universe = kg.q(f"select * from standard s {where} order by course_label, grade_band, code_norm", *vals)
    if not (args.level or args.course or args.grade):
        levels = {s["level"] for s in kg.q("select level from standard where code_norm in (%s)" % ",".join("?" * len(covered)), *covered)} if covered else set()
        universe = [s for s in universe if s["level"] in levels]
    by = defaultdict(lambda: [0, 0])
    uncovered = []
    for s in universe:
        k = (LEVEL_KO.get(s["level"]), s["course_label"], s["grade_band"] or "-")
        by[k][1] += 1
        if s["code_norm"] in covered:
            by[k][0] += 1
        else:
            uncovered.append(s)
    unknown = sorted(c for c in covered if not kg.q("select 1 from standard where code_norm=?", c))
    o = [f"# 교육과정 커버리지: {args.map}", "",
         f"매핑 행 {len(mrows)}개, 매핑된 성취기준 {len(covered)}개, 대상 범위 성취기준 {len(universe)}개", "",
         "| 학교급 | 과목 | 학년(군) | 다룸 | 전체 | 비율 |", "|--------|------|----------|------|------|------|"]
    for (lv, course, grade), (c, n) in sorted(by.items()):
        o.append(f"| {lv} | {course} | {grade} | {c} | {n} | {c / n:.0%} |")
    if unknown:
        o += ["", f"## 지식그래프에 없는 코드 {len(unknown)}개 (오타·표기 확인)", ""] + [f"- `{c}`" for c in unknown]
    holes = {}
    for s in universe:
        if s["code_norm"] not in covered:
            continue
        for ns, e in kg.neighbor_standards(s["id"], "up", "official"):
            if ns["code_norm"] not in covered:
                holes.setdefault(ns["id"], (ns, []))[1].append(s["code"])
    o += ["", f"## 빠진 공식 선수 성취기준 {len(holes)}개", "",
          "> 우리가 다루는 성취기준의 공식 선수 성취기준인데 우리 콘텐츠에는 없는 것. 진단·복습 콘텐츠 후보입니다.", ""]
    for ns, deps in sorted(holes.values(), key=lambda x: x[0]["code_norm"]):
        o.append(f"- {std_line(ns)} → 필요한 곳: {', '.join(sorted(set(deps)))}")
    o += ["", f"## 다루지 않은 성취기준 {len(uncovered)}개 (최대 {args.limit})", ""]
    o += [f"- {std_line(s)}" for s in uncovered[: args.limit]]
    return "\n".join(o) + footer(kg)


def cmd_gaps(kg: KG, args) -> str:
    bnd = json.loads(kg.meta("gap_boundaries") or "[]")
    o = ["# 전환기 학습 격차 (문서상 연계 기준)", "", "> " + " ".join(bnd), ""]
    if not args.subject:
        for tr in ([args.transition] if args.transition else ["e2m", "m2h"]):
            o += [f"## {'초→중' if tr=='e2m' else '중→고 (공통 과목)'}", "",
                  "| 순위 | 과목 | 격차 점수 | 연계율 | 신규 성취기준 | 학습량 배율 | 과목 분화 | 비고 |",
                  "|------|------|-----------|--------|---------------|-------------|-----------|------|"]
            rows = kg.q("select * from gap_profile where transition=? order by gap_score desc", tr)
            new_start = [r for r in rows if tr == "e2m" and not r["counterpart"]]
            ranked = [r for r in rows if r not in new_start]
            for i, r in enumerate(ranked[: args.top], 1):
                note = ["연계 과소집계 가능"] if r["mining_caveat"] else []
                o.append(f"| {i} | {r['subject']} | {r['gap_score']} | {r['coverage_pct']}% | {r['std_unlinked']}/{r['std_total']} | "
                         f"{r['density_ratio']} | {'예' if r['structure_split'] else ''} | {', '.join(note)} |")
            if new_start:
                o += ["", f"**중학교에서 새로 시작하는 과목 {len(new_start)}개** (초등 대응 과목 없음, 격차 점수 100으로 별도 표시): "
                      + ", ".join(f"{r['subject']}({r['std_total']})" for r in new_start)]
            o.append("")
        fs = kg.q("select * from field_signal order by subject, grade, year")
        if fs:
            o += ["## 참고: 국가수준 학업성취도 평가 기초학력 미달 비율 (표집, 비교 참고용)", "", "| 과목 | 학년 | 연도 | 미달 % |", "|------|------|------|--------|"]
            o += [f"| {r['subject']} | {r['grade']} | {r['year']} | {r['below_basic_pct']} |" for r in fs]
        return "\n".join(o) + footer(kg)
    rows = kg.q("select * from gap_profile where subject like ?" + (" and transition=?" if args.transition else ""),
                f"%{args.subject}%", *([args.transition] if args.transition else []))
    if not rows:
        return f"'{args.subject}' 격차 프로필이 없습니다. `gaps`로 과목명을 확인하세요."
    for r in rows:
        tr = r["transition"]
        o += [f"## {r['subject']} ({'초→중' if tr=='e2m' else '중→고'})", "", "| 지표 | 값 |", "|------|----|",
              f"| 격차 점수 | {r['gap_score']} |", f"| 연계율 | {r['coverage_pct']}% ({r['std_linked']}/{r['std_total']}) |",
              f"| 학습량 배율 (연간 성취기준 수) | {r['density_lower']} → {r['density_upper']} ({r['density_ratio']}배) |",
              f"| 이전 학교급 대응 과목 | {r['counterpart'] or '없음 (새로 시작)'} |",
              f"| 과목 분화 | {'해당없음 (새 과목)' if tr == 'e2m' and not r['counterpart'] else ('예' if r['structure_split'] else '아니오')} |"]
        intro = kg.q("select intro from subject_intro where subject=?", r["subject"])
        if intro:
            o.append(f"| 과목 소개 (AI 초안) | {intro[0][0]} |")
        o += ["", "### 새로 나오는 성취기준 (영역별)", ""]
        cur = None
        for n in kg.q("""select g.*, s.summary from gap_new_concept g left join standard s on s.id=g.standard_id
                         where g.transition=? and g.subject=? order by g.domain, g.code_norm""", tr, r["subject"]):
            if n["domain"] != cur:
                cur = n["domain"]; o.append(f"**{cur}**")
            o.append(f"- `{n['code']}` {n['summary'] or n['label']} — 쉬운 말: {n['easy_label'] or '-'}")
        ev = kg.q("select * from gap_evidence where transition=? and subject=? limit 8", tr, r["subject"])
        if ev:
            o += ["", "### 문서상 연계 근거 (일부)", ""]
            o += [f"- {e['lower_label'] or e['lower_code']} → `{e['upper_code']}` ({e['basis']})" for e in ev]
        o.append("")
    o.append("> 쉬운 설명은 AI 초안(ai-draft)입니다. 학부모·학생에게 쓰기 전 검토하고, '뒤처짐·부족·미달·선행학습·불안' 같은 표현을 쓰지 않습니다.")
    return "\n".join(o) + footer(kg)


def cmd_courses(kg: KG, args) -> str:
    cond, vals = [], []
    if args.level:
        cond.append("level=?"); vals.append(args.level)
    if args.category:
        cond.append("category=?"); vals.append(args.category)
    where = ("where " + " and ".join(cond)) if cond else ""
    o = ["# 과목 목록", "", "| 학교급 | 교과(군) | 과목 | 분류 | 성취기준 수 |", "|--------|----------|------|------|-------------|"]
    for c in kg.q(f"select c.*, (select count(*) from standard s where s.course_id=c.id) n from course c {where} order by level, subject_group, label", *vals):
        o.append(f"| {LEVEL_KO.get(c['level'])} | {c['subject_group'] or ''} | {c['label']} | {c['category'] or ''} | {c['n']} |")
    rel = kg.q("""select r.*, a.label fl, b.label tl from course_relation r left join course a on a.id=r.from_course
                  left join course b on b.id=r.to_course order by fl""")
    if rel and args.level in (None, "high"):
        o += ["", "## 고교 과목 간 권장 순서 (공식 문서 근거, 이수 제약 아님)", ""]
        o += [f"- {r['fl']} → {r['tl']} ({r['basis']})" for r in rel]
    return "\n".join(o) + footer(kg)


def cmd_export(kg: KG, args) -> str:
    items = []
    if args.map:
        for r in read_map(args.map):
            items.append((r.get("대상명") or r.get("대상ID") or "", r.get("관계") or "", r["성취기준코드"]))
    else:
        items = [("", "", c) for c in args.codes.split(",") if c.strip()]
    o = ["# 성취기준 정합표", "", "| 대상 | 관계 | 성취기준 | 학교급·과목 | 학년(군) | 영역 | 요약 | 근거 위치 |",
         "|------|------|----------|-------------|----------|------|------|-----------|"]
    for name, rel, code in items:
        rows = kg.find_standard(code)
        if not rows:
            o.append(f"| {name} | {rel} | `{code}` | 지식그래프에 없음 | | | | |")
            continue
        s = rows[0]
        o.append(f"| {name} | {rel} | `{s['code']}` | {LEVEL_KO.get(s['level'])} {s['course_label']} | {s['grade_band'] or '-'} | "
                 f"{s['domain_label'] or ''} | {s['summary']} | {locator(s)} |")
    o.append("\n요약은 공식 성취기준 원문이 아닌 요약문입니다. 제출 문서에서 원문이 필요하면 근거 위치의 공식 고시 문서에서 확인해 인용합니다.")
    return "\n".join(o) + footer(kg)


def main() -> int:
    ap = argparse.ArgumentParser(description="교육과정 지식그래프 조회")
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "curriculum-kg" / "kg.db")
    ap.add_argument("--out", type=Path)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def scope(p):
        p.add_argument("--level", choices=["elementary", "middle", "high", "vocational"])
        p.add_argument("--course", help="과목명 일부 (예: 수학, 공통수학1)")
        p.add_argument("--grade", help="초등 학년군 1-2 / 3-4 / 5-6, 중학교 7-9")
        p.add_argument("--limit", type=int, default=40)

    sub.add_parser("stats")
    p = sub.add_parser("search"); p.add_argument("words", nargs="+"); scope(p)
    p = sub.add_parser("standard"); p.add_argument("code")
    p = sub.add_parser("path"); p.add_argument("code"); p.add_argument("--down", action="store_true")
    p.add_argument("--up", action="store_true"); p.add_argument("--layer", choices=["official", "all"], default="official")
    p.add_argument("--depth", type=int, default=3)
    p = sub.add_parser("seed"); p.add_argument("code"); p.add_argument("--all", action="store_true")
    p = sub.add_parser("align"); p.add_argument("text", nargs="+"); scope(p)
    p = sub.add_parser("coverage"); p.add_argument("map", type=Path); scope(p)
    p = sub.add_parser("gaps"); p.add_argument("--transition", choices=["e2m", "m2h"]); p.add_argument("--subject")
    p.add_argument("--top", type=int, default=15)
    p = sub.add_parser("courses"); p.add_argument("--level", choices=["elementary", "middle", "high", "vocational"]); p.add_argument("--category")
    p = sub.add_parser("export"); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--map", type=Path); g.add_argument("--codes")
    args = ap.parse_args()

    kg = KG(args.db)
    out = globals()[f"cmd_{args.cmd}"](kg, args)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(out, encoding="utf-8")
        print(f"저장: {args.out}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
