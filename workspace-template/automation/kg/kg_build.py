#!/usr/bin/env python3
"""교육과정 지식그래프 빌더

DECK6의 세 저장소(초등 학습지도, 중등 학습지도, 전환기 격차 지도)의 정규 JSON을 읽어
하나의 SQLite 파일(data/curriculum-kg/kg.db)로 정규화한다. 저장소의 코드는 실행하지 않는다.

사용:
  python3 automation/kg/kg_build.py                       # 초등 + 중학교 + 고등(일반) + 연결 + 격차
  python3 automation/kg/kg_build.py --with-vocational     # 고교 직업계 528과목 포함 (DB가 크게 늘어남)
  python3 automation/kg/kg_build.py --src <dir> --db <path>

정규화 규칙:
  - 성취기준 코드: 대괄호·공백을 뺀 code_norm 으로도 저장 (예: [2국01-01] -> 2국01-01)
  - 선수 관계: 항상 prereq_id(먼저) -> dependent_id(나중). layer = official | candidate
  - 중->고 연결(transition-alignments)은 from x to 토픽 쌍으로 펼쳐 edge_set='middle->high'
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = """
create table meta(key text primary key, value text);
create table release(repo text, profile text, release_id text, commit_sha text, license text, note text);
create table course(id text primary key, level text, label text, subject_group text, category text, grade_scope text);
create table domain(id text primary key, level text, course_id text, label text);
create table standard(
  id text primary key, level text, code text, code_norm text, course_id text, course_label text,
  domain_id text, domain_label text, grade_band text, summary text,
  source_id text, printed_page integer, pdf_page integer, section text,
  review_status text, verification_status text);
create table topic(
  id text primary key, level text, label text, description text, types text,
  facet_key text, facet_detail text, topic_role text, collapse_into text, collapse_reason text,
  grade_band text, course_label text, domain_label text, content_kind text,
  evidence text, assessment_prompts text, misconceptions text, review_status text);
create table alignment(topic_id text, standard_id text, kind text, confidence text, basis text);
create table edge(
  id text, prereq_id text, dependent_id text, layer text, relation_kind text, strength text,
  scope text, basis_kind text, basis text, reason text, review_status text, edge_set text);
create table course_relation(id text, from_course text, to_course text, relation_kind text,
  claim_status text, basis text, reason text);
create table cluster(id text primary key, level text, label text, summary text, parent_summary text, grade_band text);
create table cluster_topic(cluster_id text, topic_id text);
create table coverage_gap(id text, repo text, severity text, status text, description text);
create table policy(kind text, id text, label text, body text);
create table gap_profile(
  transition text, subject text, counterpart text, subject_group text, course_category text,
  gap_score integer, coverage_pct real, unlinked_ratio real, density_lower real, density_upper real,
  density_ratio real, structure_split integer, mining_caveat integer,
  std_total integer, std_linked integer, std_unlinked integer, field_evidence integer);
create table gap_new_concept(transition text, subject text, standard_id text, code text, code_norm text,
  domain text, label text, easy_label text, easy_explain text);
create table gap_evidence(transition text, subject text, transition_id text, lower_topic_id text, lower_code text,
  lower_label text, upper_topic_id text, upper_code text, basis text, page integer);
create table field_signal(subject text, grade text, year text, below_basic_pct real, cross_delta real, signal text);
create table subject_intro(subject text, intro text);
create table unresolved(kind text, ref text, note text);
"""

INDEXES = """
create index ix_std_code on standard(code_norm);
create index ix_std_level on standard(level, course_label, grade_band);
create index ix_al_topic on alignment(topic_id);
create index ix_al_std on alignment(standard_id);
create index ix_edge_pre on edge(prereq_id);
create index ix_edge_dep on edge(dependent_id);
create index ix_gnc_code on gap_new_concept(code_norm);
"""


def norm_code(code: str | None) -> str | None:
    if not code:
        return None
    return re.sub(r"[\[\]\s]", "", code).replace("Ⅰ", "I").replace("Ⅱ", "II")


def load(p: Path):
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def j(x) -> str:
    return json.dumps(x or [], ensure_ascii=False)


def build_elementary(db, src: Path, lock: dict):
    base = src / "data" / "kr"
    cs = load(base / "curriculum-standards.json")
    db.execute("insert into release values(?,?,?,?,?,?)",
               ("elementary", "elementary", lock.get("release"), lock.get("commit"), lock.get("license"), cs.get("taxonomyVersion")))
    for c in cs["curricula"]:
        db.execute("insert into course values(?,?,?,?,?,?)",
                   (c["id"], "elementary", c["subjectKorean"], c["subjectKorean"], "common", "1-6"))
        for s in c["standards"]:
            db.execute("insert into standard values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                s["key"], "elementary", s["code"], norm_code(s["code"]), c["id"], c["subjectKorean"],
                None, s.get("domainKorean"), s.get("gradeBand"), s.get("summary"),
                (s.get("sourceRefs") or [None])[0], None, None, s.get("sourceSection"),
                None, s.get("verificationStatus")))
    for m in cs.get("standardMappings", []):
        db.execute("insert into alignment values(?,?,?,?,?)",
                   (m["microTopicId"], m["standardKey"], m.get("relationship"), m.get("confidence"), m.get("note")))
    for g in cs.get("coverageGaps", []):
        db.execute("insert into coverage_gap values(?,?,?,?,?)",
                   (g["id"], "elementary", g.get("severity"), g.get("status"), g.get("description") or g.get("note")))

    for t in load(base / "topics.json")["topics"]:
        db.execute("insert into topic values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            t["id"], "elementary", t.get("titleKorean") or t.get("name"), t.get("description"), t.get("type"),
            t.get("facetKey"), None, t.get("topicRole"), t.get("collapseInto"), t.get("collapseReason"),
            t.get("gradeBand"), t.get("subjectKorean"), t.get("domainKorean"), t.get("contentKind"),
            j(t.get("evidence")), j([t["assessmentPrompt"]] if t.get("assessmentPrompt") else []),
            j(t.get("misconceptions")), t.get("verificationStatus")))

    for fname, layer in (("dependencies.json", "official"), ("dependencies.candidate.json", "candidate")):
        for e in load(base / fname)["dependencies"]:
            strength = "required" if layer == "official" else ("recommended" if e.get("strength") == "soft" else "recommended-strong")
            db.execute("insert into edge values(?,?,?,?,?,?,?,?,?,?,?,?)", (
                e["id"], e["prerequisiteId"], e["topicId"], layer, e.get("relationKind"), strength,
                e.get("scope"), e.get("basisKind"), e.get("basis"), e.get("reason"), e.get("reviewStatus"), "elementary"))

    for c in load(base / "clusters.json")["clusters"]:
        db.execute("insert into cluster values(?,?,?,?,?,?)",
                   (c["id"], "elementary", c.get("titleKorean") or c.get("name"), c.get("summary"), c.get("parentSummary"), c.get("gradeBand")))
        for tid in c.get("topics", []):
            db.execute("insert into cluster_topic values(?,?)", (c["id"], tid))


def collection_paths(rel_dir: Path, release: dict, name: str) -> list[Path]:
    v = release["collections"].get(name)
    if v is None:
        return []
    return [rel_dir / p for p in ([v] if isinstance(v, str) else v)]


def records(paths: list[Path]):
    for p in paths:
        for r in load(p)["records"]:
            yield r


def build_secondary_level(db, base: Path, level: str, lock: dict):
    d = base / level
    rel = load(d / "release.json")
    lvl = "vocational" if level == "high-vocational" else level
    db.execute("insert into release values(?,?,?,?,?,?)",
               ("secondary", level, rel["releaseId"], lock.get("commit"), lock.get("license"), rel.get("rightsStatus")))
    groups = {g["id"]: g["labelKorean"] for g in records(collection_paths(d, rel, "subjectGroups"))}
    courses = {}
    for c in records(collection_paths(d, rel, "courses")):
        courses[c["id"]] = c["labelKorean"]
        db.execute("insert into course values(?,?,?,?,?,?)", (
            c["id"], lvl, c["labelKorean"], groups.get(c.get("subjectGroupId")), c.get("courseCategory"),
            ",".join(c.get("gradeScope") or []) or None))
    domains = {}
    for dm in records(collection_paths(d, rel, "domains")):
        domains[dm["id"]] = dm["labelKorean"]
        db.execute("insert into domain values(?,?,?,?)", (dm["id"], lvl, dm.get("courseId"), dm["labelKorean"]))
    grade = "7-9" if lvl == "middle" else None
    for s in records(collection_paths(d, rel, "standards")):
        loc = s.get("sourceLocator") or {}
        db.execute("insert into standard values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            s["id"], lvl, s["code"], norm_code(s["code"]), s.get("courseId"), courses.get(s.get("courseId")),
            s.get("domainId"), domains.get(s.get("domainId")), grade, s.get("summary"),
            loc.get("sourceId"), loc.get("printedPage"), loc.get("pdfPage"), loc.get("section"),
            s.get("reviewStatus"), s.get("verificationStatus")))
    for t in records(collection_paths(d, rel, "topics")):
        cid = (t.get("courseIds") or [None])[0]
        db.execute("insert into topic values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            t["id"], lvl, t.get("labelKorean"), t.get("description"), ",".join(t.get("types") or []),
            t.get("facetKey"), t.get("facetKeyDetail"), t.get("topicRole"), t.get("collapseInto"), t.get("collapseReason"),
            grade, courses.get(cid), domains.get(t.get("domainId")), t.get("contentKind"),
            j(t.get("evidence")), j(t.get("assessmentPrompts")), j(t.get("misconceptions")), t.get("reviewStatus")))
        for a in t.get("standardAlignments") or []:
            db.execute("insert into alignment values(?,?,?,?,?)",
                       (t["id"], a["standardId"], a.get("alignmentKind"), None, a.get("basis")))
    for name, layer in (("learningRelations", "official"), ("candidateLearningRelations", "candidate")):
        for e in records(collection_paths(d, rel, name)):
            db.execute("insert into edge values(?,?,?,?,?,?,?,?,?,?,?,?)", (
                e["id"], e["prerequisiteTopicId"], e["dependentTopicId"], layer, e.get("relationKind"),
                e.get("strength"), e.get("scope"), e.get("basisKind"), e.get("basis"), e.get("reason"),
                e.get("reviewStatus"), lvl))
    for c in records(collection_paths(d, rel, "clusters")):
        db.execute("insert into cluster values(?,?,?,?,?,?)", (c["id"], lvl, c.get("labelKorean"), c.get("summary"), None, grade))
        for tid in c.get("topicIds", []):
            db.execute("insert into cluster_topic values(?,?)", (c["id"], tid))
    for g in records(collection_paths(d, rel, "coverageGaps")):
        db.execute("insert into coverage_gap values(?,?,?,?,?)",
                   (g["id"], f"secondary/{level}", g.get("severity"), g.get("status"), g.get("description")))
    for r in records(collection_paths(d, rel, "courseRelations")):
        db.execute("insert into course_relation values(?,?,?,?,?,?,?)", (
            r["id"], r["fromCourseId"], r["toCourseId"], r.get("relationKind"), r.get("claimStatus"), r.get("basis"), r.get("reason")))
    for kind in ("creditRules", "choiceSets", "pathways"):
        for r in records(collection_paths(d, rel, kind)):
            db.execute("insert into policy values(?,?,?,?)", (kind, r.get("id"), r.get("labelKorean"), json.dumps(r, ensure_ascii=False)))


def build_bridges(db, base: Path, lock: dict):
    d = base / "bridges"
    rel = load(d / "release.json")
    db.execute("insert into release values(?,?,?,?,?,?)",
               ("secondary", "bridges", rel["releaseId"], lock.get("commit"), lock.get("license"), rel.get("rightsStatus")))
    for name, layer in (("elementaryTransitions", "official"), ("candidateElementaryTransitions", "candidate")):
        for e in records(collection_paths(d, rel, name)):
            db.execute("insert into edge values(?,?,?,?,?,?,?,?,?,?,?,?)", (
                e["id"], e["prerequisiteTopicId"], e["dependentTopicId"], layer, e.get("relationKind"),
                e.get("strength"), e.get("scope"), e.get("basisKind"), e.get("basis"), e.get("reason"),
                e.get("reviewStatus"), "elementary->middle"))
    for e in records(collection_paths(d, rel, "transitionAlignments")):
        for f in e.get("fromTopicIds", []):
            for t in e.get("toTopicIds", []):
                db.execute("insert into edge values(?,?,?,?,?,?,?,?,?,?,?,?)", (
                    e["id"], f, t, "official", e.get("transitionKind", "deepens"), "recommended",
                    "cross-school-level", e.get("basisKind"), e.get("basis"), e.get("reason"),
                    e.get("reviewStatus"), "middle->high"))
    for g in records(collection_paths(d, rel, "coverageGaps")):
        db.execute("insert into coverage_gap values(?,?,?,?,?)",
                   (g["id"], "secondary/bridges", g.get("severity"), g.get("status"), g.get("description")))


def build_gap(db, src: Path, lock: dict):
    g = load(src / "data" / "gap-report.json")
    labels = load(src / "data" / "easy-labels.json")
    db.execute("insert into release values(?,?,?,?,?,?)",
               ("gap", "transition-gap", g.get("version"), lock.get("commit"), lock.get("license"),
                json.dumps(g.get("generatedFrom"), ensure_ascii=False)))
    db.execute("insert into meta values('gap_boundaries', ?)", (json.dumps(g.get("boundaries"), ensure_ascii=False),))
    db.execute("insert into meta values('easy_labels_review', ?)", (labels.get("reviewStatus"),))
    lab = labels.get("labels", {})
    for tkey, tname, listkey, namekey in (("elementaryToMiddle", "e2m", "subjects", "subject"),
                                          ("middleToHigh", "m2h", "courses", "course")):
        for s in g["transitions"][tkey][listkey]:
            name = s[namekey]
            dj = s.get("densityJump") or {}
            st = s.get("standards") or {}
            db.execute("insert into gap_profile values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                tname, name, s.get("elementaryCounterpart"), s.get("subjectGroup"), s.get("courseCategory"),
                s.get("gapScore"), s.get("coveragePct"), s.get("unlinkedRatio"), dj.get("lowerPerYear"),
                dj.get("upperPerYear"), dj.get("ratio"), int(bool(s.get("structureSplit"))),
                int(bool(s.get("miningDensityCaveat"))), st.get("total"), st.get("linked"), st.get("unlinked"),
                int(bool(s.get("fieldEvidenceRef")))))
            for n in s.get("newlyIntroduced", []):
                el = lab.get(n.get("standardId"), {})
                db.execute("insert into gap_new_concept values(?,?,?,?,?,?,?,?,?)", (
                    tname, name, n.get("standardId"), n.get("code"), norm_code(n.get("code")), n.get("domain"),
                    n.get("label"), el.get("easyLabel"), el.get("easyExplain")))
            for ev in s.get("linkedEvidence", []):
                if tname == "e2m":
                    row = (ev.get("transitionId"), ev.get("elementaryTopicId"), None, ev.get("elementaryLabel"),
                           None, ev.get("middleCode"))
                else:
                    row = (ev.get("transitionId"), ev.get("middleTopicId"), ev.get("middleCode"), ev.get("middleLabel"),
                           ev.get("highTopicId"), ev.get("highCode"))
                db.execute("insert into gap_evidence values(?,?,?,?,?,?,?,?,?,?)",
                           (tname, name, *row, ev.get("basis"), ev.get("page")))
    fe = g.get("fieldEvidence") or {}
    db.execute("insert into meta values('field_evidence_source', ?)", (json.dumps(fe.get("source"), ensure_ascii=False),))
    for s in fe.get("subjects", []):
        for grade, key in (("중3", "middle3"), ("고2", "high2")):
            for year, v in (s.get(key) or {}).items():
                db.execute("insert into field_signal values(?,?,?,?,?,?)", (
                    s["subject"], grade, year, v, (s.get("crossSectionDelta") or {}).get(year), " / ".join(s.get("signal") or [])))
    intros = labels.get("subjectIntros", {})
    for k, v in (intros.items() if isinstance(intros, dict) else []):
        db.execute("insert into subject_intro values(?,?)", (k, v))


def check_joins(db) -> dict:
    q = {
        "alignment_topic_missing": "select count(*) from alignment a left join topic t on t.id=a.topic_id where t.id is null",
        "alignment_standard_missing": "select count(*) from alignment a left join standard s on s.id=a.standard_id where s.id is null",
        "edge_prereq_missing": "select count(*) from edge e left join topic t on t.id=e.prereq_id where t.id is null",
        "edge_dependent_missing": "select count(*) from edge e left join topic t on t.id=e.dependent_id where t.id is null",
        "gap_new_concept_standard_missing": "select count(*) from gap_new_concept g left join standard s on s.id=g.standard_id where s.id is null",
        "gap_evidence_lower_topic_missing": "select count(*) from gap_evidence g left join topic t on t.id=g.lower_topic_id where t.id is null",
    }
    res = {k: db.execute(v).fetchone()[0] for k, v in q.items()}
    for row in db.execute("select g.standard_id, g.code from gap_new_concept g left join standard s on s.id=g.standard_id where s.id is null limit 200"):
        db.execute("insert into unresolved values('gap_new_concept', ?, ?)", row)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="교육과정 지식그래프 빌더")
    ap.add_argument("--src", type=Path, default=ROOT / "data" / "curriculum-kg" / "src")
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "curriculum-kg" / "kg.db")
    ap.add_argument("--lock", type=Path, default=ROOT / "automation" / "kg" / "sources.lock.json")
    ap.add_argument("--with-vocational", action="store_true")
    args = ap.parse_args()

    lock = {s["key"]: s for s in load(args.lock)["sources"]}
    paths = {k: args.src / k for k in ("elementary", "secondary", "gap")}
    for k, p in paths.items():
        if not p.exists():
            print(f"원천 저장소가 없습니다: {p}\n먼저 automation/kg/kg_sync.sh 를 실행하세요.", file=sys.stderr)
            return 1

    args.db.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.db.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.executescript(SCHEMA)
    build_elementary(db, paths["elementary"], lock["elementary"])
    sec = paths["secondary"] / "data" / "kr"
    for level in ["middle", "high"] + (["high-vocational"] if args.with_vocational else []):
        build_secondary_level(db, sec, level, lock["secondary"])
    build_bridges(db, sec, lock["secondary"])
    build_gap(db, paths["gap"], lock["gap"])
    db.executescript(INDEXES)
    joins = check_joins(db)
    db.execute("insert into meta values('join_check', ?)", (json.dumps(joins),))
    db.execute("insert into meta values('attribution', ?)", (
        "교육과정 지식그래프 데이터: DECK6 korean-elementary-learning-map, korean-secondary-learning-map, "
        "transition-gap-map (MIT License, (c) 2026 DECK). 공식 근거: 교육부·국가교육위원회 고시 및 별책(NCIC 제공). "
        "교육부·국가교육위원회·NCIC의 승인·공식 해석이 아니며 개별 학습자를 진단하지 않는다.",))
    db.commit()
    db.close()
    tmp.replace(args.db)

    db = sqlite3.connect(args.db)
    print(f"생성: {args.db}")
    for row in db.execute("select level, count(*) from standard group by level order by 1"):
        print(f"  성취기준 {row[0]}: {row[1]}")
    for row in db.execute("select level, count(*) from topic group by level order by 1"):
        print(f"  토픽 {row[0]}: {row[1]}")
    for row in db.execute("select edge_set, layer, count(*) from edge group by 1,2 order by 1,2"):
        print(f"  관계 {row[0]} [{row[1]}]: {row[2]}")
    print(f"  격차 프로필 {db.execute('select count(*) from gap_profile').fetchone()[0]}, "
          f"신규 성취기준 {db.execute('select count(*) from gap_new_concept').fetchone()[0]}")
    bad = {k: v for k, v in joins.items() if v}
    print("  연결 점검:", "모두 연결됨" if not bad else bad)
    if bad:
        print("  (원천 저장소 버전 차이로 생긴 끊긴 참조입니다. kg_query 결과에서 해당 항목은 '연결 안 됨'으로 표시됩니다.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
