"""EdPM 프레임워크 스크립트 회귀 테스트. 표준 라이브러리만. 실행: python3 -m unittest discover -s tests -v

템플릿 워크스페이스를 임시 폴더에 복사해 edpm_check·pre_write 훅·wbs_sync(가짜 gh)·metrics를 실제로 실행한다.
"""
from __future__ import annotations

import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FW = Path(__file__).resolve().parents[1]
TEMPLATE = FW / "workspace-template"
FAKE_GH = r'''#!/usr/bin/env python3
import json, sys, os
p = os.environ["FAKE_GH_STATE"]
st = json.load(open(p)) if os.path.exists(p) else {"issues": {}, "milestones": {}, "items": {}}
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
out = ""
if a[:2] == ["issue", "list"]: out = json.dumps(list(st["issues"].values()))
elif a[:2] == ["issue", "create"]:
    n = len(st["issues"]) + 1
    st["issues"][str(n)] = {"number": n, "state": "OPEN", "title": opt("--title"), "body": opt("--body"),
        "labels": [{"name": x} for x in opt("--label", "").split(",") if x], "assignees": [], "milestone": {"title": opt("--milestone")}, "url": f"https://x/issues/{n}"}
    out = st["issues"][str(n)]["url"] + "\n"
elif a[:2] == ["issue", "edit"]:
    i = st["issues"][a[2]]; i["title"] = opt("--title"); i["body"] = opt("--body")
    names = {l["name"] for l in i["labels"]} | set(opt("--add-label", "").split(",")) - set(opt("--remove-label", "").split(","))
    i["labels"] = [{"name": x} for x in names if x]; i["milestone"] = {"title": opt("--milestone")}
elif a[:2] == ["issue", "close"]: st["issues"][a[2]]["state"] = "CLOSED"
elif a[0] == "api" and "-X" not in a: out = json.dumps([{"title": t, "number": n} for t, n in st["milestones"].items()])
elif a[0] == "api":
    f = dict(x.split("=", 1) for x in [a[i + 1] for i, v in enumerate(a) if v == "-f"])
    if opt("-X") == "POST": st["milestones"][f["title"]] = len(st["milestones"]) + 1
json.dump(st, open(p, "w"), ensure_ascii=False); print(out, end="")
'''


def run(args, cwd, env=None, stdin=None):
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, input=stdin,
                          env={**os.environ, **(env or {})})


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="edpm-test-"))
        self.ws = self.tmp / "ws"
        shutil.copytree(TEMPLATE, self.ws, symlinks=True)
        shutil.copytree(FW / "brain-seed" / "domain", self.ws / "02.wiki" / "domain", dirs_exist_ok=True)  # install.sh와 같게
        self.env = {"EDPM_ROOT": str(self.ws), "CLAUDE_PROJECT_DIR": str(self.ws)}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def doc(self, rel):
        return self.ws / "03.docs" / rel

    def set_status(self, rel, status):
        p = self.doc(rel)
        s = p.read_text(encoding="utf-8")
        s = s.replace("status: draft        # draft | review | done | n/a", f"status: {status}", 1)
        s = s.replace("updated: YYYY-MM-DD", "updated: 2026-10-01", 1)
        p.write_text(s, encoding="utf-8")

    def set_prd(self, status):
        p = self.ws / "PRD.md"
        s = p.read_text(encoding="utf-8")
        s = re.sub(r"^status:.*$", f"status: {status}", s, count=1, flags=re.M)
        p.write_text(s, encoding="utf-8")

    def set_agents(self, key, value):
        p = self.ws / "AGENTS.md"
        s = p.read_text(encoding="utf-8")
        s = re.sub(rf"^\| {re.escape(key)} \|.*$", f"| {key} | {value} |", s, count=1, flags=re.M)
        p.write_text(s, encoding="utf-8")

    def check(self, *args):
        return run([self.ws / "automation/scripts/edpm_check.py", *args], self.ws, self.env)

    def hook(self, tool, file_path, **tool_input):
        payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": str(file_path), **tool_input}})
        return run([self.ws / "automation/hooks/pre_write.py"], self.ws, self.env, payload)


class CheckTests(WorkspaceCase):
    def test_brief_runs_and_counts_docs(self):
        r = run([self.ws / "automation/scripts/edpm_check.py", "json"], self.ws, self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertGreaterEqual(data["docs"]["total"], 70)
        self.assertEqual(data["pii"], [])
        self.assertLessEqual(len(data["wiki"]["broken_links"]), 1, f"템플릿 자체의 끊긴 링크: {data['wiki']['broken_links']}")

    def test_gate_blocks_until_prereqs_done(self):
        e09 = self.doc("3.설계/E09_기능명세서.md")
        r = run([self.ws / "automation/scripts/edpm_check.py", "gate", e09], self.ws, self.env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("G-LEARN", r.stdout)
        for rel in ("0.온보딩/E00_회사사업프로필.md", "1.발견/E01_교육문제정의서.md", "1.발견/E02_이해관계자맵.md",
                    "1.발견/E03_현장리서치종합.md", "1.발견/E04_시장정책분석.md", "2.정의/E05_학습성과설계서.md",
                    "2.정의/E06_제품요구사항서.md", "3.설계/E08_학습경험설계서.md"):
            self.set_status(rel, "done")
        r = run([self.ws / "automation/scripts/edpm_check.py", "gate", e09], self.ws, self.env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("G-PRD", r.stdout, "PRD가 draft면 전제가 다 done이어도 막혀야 함")
        self.set_prd("review")
        r = run([self.ws / "automation/scripts/edpm_check.py", "gate", e09], self.ws, self.env)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_blocked_done_is_reported(self):
        self.set_status("3.설계/E09_기능명세서.md", "done")
        data = json.loads(run([self.ws / "automation/scripts/edpm_check.py", "json"], self.ws, self.env).stdout)
        self.assertTrue(any(x.startswith("E09") for x in data["docs"]["blocked_done"]))

    def test_pii_detection(self):
        f = self.tmp / "x.md"
        f.write_text("학부모 연락처 010-1234-5678", encoding="utf-8")
        self.assertEqual(run([self.ws / "automation/scripts/edpm_check.py", "pii", f], self.ws, self.env).returncode, 1)
        f.write_text("학부모B는 주 3회 사용, 문의 support@example.com", encoding="utf-8")
        self.assertEqual(run([self.ws / "automation/scripts/edpm_check.py", "pii", f], self.ws, self.env).returncode, 0)


    def test_content_gate_measure_on_f02(self):
        rel = "F.개선/202610_게이트테스트"
        shutil.copytree(self.doc("F.개선/_과제템플릿"), self.doc(rel))
        chk = self.ws / "automation/scripts/edpm_check.py"
        f02 = self.doc(rel + "/F02_기능기획서.md")
        self.set_prd("review")
        r = run([chk, "gate", f02], self.ws, self.env)
        self.assertIn("G-MEASURE", r.stdout)  # 플레이스홀더 지표만 있으면 미충족
        self.set_status(rel + "/F01_문제정의서.md", "done")
        self.set_status(rel + "/F02_기능기획서.md", "done")
        t = f02.read_text(encoding="utf-8").replace(
            "| 주 지표 | {M-xx} | {…} | {…} | {…} | {출시 후 N주} | `automation/sql/{…}.sql` |",
            "| 주 지표 | M-10 | 과제 제출률 | 55% (9월) | 70% | 출시 후 6주 | `automation/sql/제출률.sql` |", 1)
        f02.write_text(t, encoding="utf-8")
        r = run([chk, "gate", f02], self.ws, self.env)
        self.assertEqual(r.returncode, 0, r.stdout)  # 실제 지표 행이 채워지면 통과

    def test_content_gate_impact_on_f03(self):
        rel = "F.개선/202610_임팩트테스트"
        shutil.copytree(self.doc("F.개선/_과제템플릿"), self.doc(rel))
        chk = self.ws / "automation/scripts/edpm_check.py"
        f02 = self.doc(rel + "/F02_기능기획서.md")
        f03 = self.doc(rel + "/F03_실험출시계획서.md")
        self.set_status(rel + "/F02_기능기획서.md", "done")
        r = run([chk, "gate", f03], self.ws, self.env)
        self.assertIn("G-IMPACT", r.stdout)  # F02 영향표가 플레이스홀더라 미처리
        # 영향표의 해당여부 플레이스홀더(첫 행 긴 형식 + 나머지 {…})를 모두 해소
        t = f02.read_text(encoding="utf-8").replace("{해당/해당없음: 사유}", "해당없음: 범위 밖").replace("{…}", "해당없음")
        f02.write_text(t, encoding="utf-8")
        r = run([chk, "gate", f03], self.ws, self.env)
        self.assertNotIn("G-IMPACT", r.stdout)  # 모두 해당없음으로 처리하면 해소


class FlowTests(WorkspaceCase):
    """PRD 원점 흐름: 단계 판정, 착수 가능 판정, frontmatter 주석, 제품 코드 게이트."""

    def test_phase_progression(self):
        self.assertIn("0 시작", self.check("phase").stdout)
        self.assertIn("처음 오셨군요", self.check("brief").stdout)
        self.set_status("0.온보딩/E00_회사사업프로필.md", "done")
        self.assertIn("1 PRD", self.check("phase").stdout)
        self.assertEqual([x.split()[0] for x in self.check("next").stdout.split("\n") if x], ["PRD"],
                         "PRD 전에는 PRD만 착수 가능")
        self.set_prd("review")
        self.assertIn("2 착수·근거", self.check("phase").stdout)
        for rel in ("M.관리/M01_착수보고서.md",):
            self.set_status(rel, "done")
        self.assertIn("3 상세 요구사항", self.check("phase").stdout)
        self.set_status("2.정의/E06_제품요구사항서.md", "done")
        self.assertIn("4 스펙", self.check("phase").stdout)
        self.set_status("3.설계/E09_기능명세서.md", "done")
        self.assertIn("5 프로토타입", self.check("phase").stdout)
        self.set_agents("개발 체계", "바이브코딩")
        self.assertIn("5 구현", self.check("phase").stdout)

    def test_next_skips_docs_whose_prereqs_are_all_na(self):
        self.set_status("0.온보딩/E00_회사사업프로필.md", "done")
        self.set_prd("review")
        self.set_status("7.측정/E19_학습효과리포트.md", "n/a")
        nxt = self.check("next").stdout
        self.assertNotIn("E20", nxt, "전제(E19)가 n/a뿐이면 회고가 시작 시점에 뜨면 안 됨")
        self.assertIn("E01", nxt)

    def test_frontmatter_single_space_comment(self):
        # A02 템플릿: "requires: [A01, B01, A10] # + A04…" — 주석 때문에 전제가 사라지면 안 됨
        self.set_status("0.온보딩/E00_회사사업프로필.md", "done")
        self.set_prd("review")
        self.assertNotIn("A02", self.check("next").stdout)

    def test_code_gate_spec_and_dev_system(self):
        src = self.ws / "src" / "app.py"
        self.set_status("0.온보딩/E00_회사사업프로필.md", "done")
        self.set_prd("review")
        r = self.hook("Write", src, content="print(1)")
        self.assertEqual(r.returncode, 2)
        self.assertIn("G-SPEC", r.stderr)
        self.set_status("3.설계/E09_기능명세서.md", "done")
        self.set_agents("개발 체계", "바이브코딩 (PM이 LLM과 구현)")
        self.assertEqual(self.hook("Write", src, content="print(1)").returncode, 0)
        self.set_agents("개발 체계", "개발팀")
        r = self.hook("Write", src, content="print(1)")
        self.assertEqual(r.returncode, 2)
        self.assertIn("개발팀", r.stderr)
        self.assertEqual(self.hook("Write", self.ws / "06.prototypes" / "PT-01_x" / "app.py", content="x").returncode, 0,
                         "프로토타입 코드는 스펙 게이트 대상 아님")


class StartGateTests(WorkspaceCase):
    """생성 게이트(A가 끝나야 B)와 진행표."""

    def test_body_write_blocked_until_prereqs_done(self):
        e01 = self.doc("1.발견/E01_교육문제정의서.md")
        old = e01.read_text(encoding="utf-8")
        new = old + "\n## 추가한 본문\n학원 강사 인터뷰 요약\n"
        r = self.hook("Write", e01, content=new)
        self.assertEqual(r.returncode, 2, "E00·PRD 전에는 E01 본문을 쓸 수 없음")
        self.assertIn("A가 끝나야 B", r.stderr)
        self.set_status("0.온보딩/E00_회사사업프로필.md", "done")
        self.set_prd("review")
        self.assertEqual(self.hook("Write", e01, content=new).returncode, 0, "전제가 끝나면 통과")

    def test_allowed_exceptions(self):
        e09 = self.doc("3.설계/E09_기능명세서.md")
        old = e09.read_text(encoding="utf-8")
        line = next(l for l in old.splitlines() if l.startswith("status:"))
        self.assertEqual(self.hook("Edit", e09, old_string=line, new_string="status: n/a").returncode, 0, "n/a 처리는 통과")
        self.assertEqual(self.hook("Edit", e09, old_string="owner: ", new_string="owner: PM").returncode, 0, "frontmatter만 바꾸면 통과")
        early = old.replace("gate_skip:", "early_draft: [사용자 지시: 개발팀 회의용 미리 초안]\ngate_skip:", 1) + "\n본문 초안\n"
        self.assertEqual(self.hook("Write", e09, content=early).returncode, 0, "early_draft 사유가 있으면 통과")
        self.assertEqual(self.hook("Write", self.doc("F.개선/_과제템플릿/F01_문제정의서.md"), content=old + "x").returncode, 0,
                         "템플릿 폴더는 대상 아님")

    def test_progress_table(self):
        out = self.check("progress").stdout
        self.assertIn("| E00 |", out)
        self.assertIn("착수 가능", out)
        self.assertIn("대기: G-PRD", out)
        self.set_status("0.온보딩/E00_회사사업프로필.md", "done")
        self.set_prd("review")
        out = self.check("progress").stdout
        self.assertIn("| PRD |", out)
        self.assertIn("검토 중 (다음 단계 열림)", out)
        self.assertRegex(out, r"\| E01 \|.*착수 가능")


class ExportTests(WorkspaceCase):
    def test_export_html_strips_guides_and_examples(self):
        out = self.tmp / "out"
        r = run([self.ws / "automation/scripts/edpm_export.py", self.ws / "PRD.md", "--out-dir", out], self.ws, self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        html_files = list(out.glob("PRD_*.html"))
        self.assertEqual(len(html_files), 1)
        page = html_files[0].read_text(encoding="utf-8")
        self.assertIn("<table>", page)
        self.assertIn("목차", page)
        self.assertNotIn("작성 가이드", page.replace("<title>", ""), "작성 가이드 인용 블록은 빠져야 함")
        self.assertNotIn("매스핏 / 중학생", page, "예시 행은 기본으로 빠져야 함")
        r = run([self.ws / "automation/scripts/edpm_export.py", self.ws / "PRD.md", "--out-dir", out, "--keep-examples"], self.ws, self.env)
        self.assertIn("매스핏", max(out.glob("PRD_*.html"), key=lambda p: p.stat().st_mtime).read_text(encoding="utf-8"))


class HookTests(WorkspaceCase):
    def test_done_transition_blocked_then_allowed_with_skip(self):
        e09 = self.doc("3.설계/E09_기능명세서.md")
        old = "status: draft        # draft | review | done | n/a"
        r = self.hook("Edit", e09, old_string=old, new_string="status: done")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("G-LEARN", r.stderr)
        r = self.hook("Edit", e09, old_string=old, new_string="status: done\ngate_skip: [사용자 지시]")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_raw_folder_append_only(self):
        f = self.ws / "01.자료실/현장/2026-10-01_인터뷰.md"
        f.write_text("교사A 인터뷰", encoding="utf-8")
        self.assertEqual(self.hook("Edit", f, old_string="교사A", new_string="교사B").returncode, 2)
        self.assertEqual(self.hook("Write", self.ws / "01.자료실/현장/2026-10-02_인터뷰.md", content="교사B 인터뷰").returncode, 0)

    def test_pii_blocked_in_wiki_only(self):
        self.assertEqual(self.hook("Write", self.ws / "02.wiki/research/x.md", content="연락처 010-9876-5432").returncode, 2)
        self.assertEqual(self.hook("Write", self.ws / "05.outputs/x.md", content="연락처 010-9876-5432").returncode, 0)

    def test_hook_ignores_other_tools_and_bad_input(self):
        self.assertEqual(run([self.ws / "automation/hooks/pre_write.py"], self.ws, self.env, "not json").returncode, 0)
        self.assertEqual(self.hook("Read", self.ws / "01.자료실/README.md").returncode, 0)


class WbsSyncTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        gh = self.tmp / "gh"
        gh.write_text(FAKE_GH, encoding="utf-8"); gh.chmod(0o755)
        self.env.update({"GH_BIN": str(gh), "FAKE_GH_STATE": str(self.tmp / "gh.json")})
        (self.ws / "03.docs/M.관리/M02_WBS.csv").write_text(
            "wp_id,이름,단계,산출물ID,담당,공수(일),시작,종료,선행,학사제약,상태,이슈\n"
            "WP-1.1,(예시) 예시,발견,E03,PM,1,2026-10-01,2026-10-02,,,예정,\n"
            "WP-1.1,현장 리서치,발견,E03,PM,5,2026-10-01,2026-10-05,,,진행,\n"
            "WP-2.1,지표 정의,정의,E05;E07,PM,3,2026-10-06,2026-10-08,WP-1.1,,완료,\n", encoding="utf-8")

    def sync(self, *args):
        return run([self.ws / "automation/scripts/wbs_sync.py", *args, "--repo", "o/r"], self.ws, self.env)

    def test_push_is_idempotent_and_pull_updates_status(self):
        r = self.sync("push"); self.assertIn("생성 2", r.stdout, r.stderr)
        csv_text = (self.ws / "03.docs/M.관리/M02_WBS.csv").read_text(encoding="utf-8")
        self.assertIn("현장 리서치,발견,E03,PM,5,2026-10-01,2026-10-05,,,진행,1", csv_text)
        r = self.sync("push"); self.assertIn("생성 0, 갱신 0, 변경 없음 2", r.stdout)
        state = json.loads((self.tmp / "gh.json").read_text())
        self.assertEqual(state["issues"]["2"]["state"], "CLOSED", "완료 WP는 이슈가 닫혀야 함")
        state["issues"]["1"]["state"] = "CLOSED"
        (self.tmp / "gh.json").write_text(json.dumps(state))
        r = self.sync("pull"); self.assertIn("진행 → 완료", r.stdout)

    def test_export_formats(self):
        for t in ("jira", "linear", "notion", "sheets"):
            r = run([self.ws / "automation/scripts/wbs_sync.py", "export", "--to", t], self.ws, self.env)
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(list((self.ws / "05.outputs").glob("wbs_*.csv"))), 4)


class MetricsTests(WorkspaceCase):
    def test_sample_db_and_templates(self):
        m = self.ws / "automation/scripts/metrics.py"
        db = self.ws / "05.outputs/sample.sqlite"
        self.assertEqual(run([m, "sample-db", db], self.ws, self.env).returncode, 0)
        common = ["--db", str(db), "--param", "from=2026-09-01", "--param", "to=2026-10-31", "--param", "course=C-MATH-1",
                  "--param", "event=lesson_completed", "--param", "n=1", "--param", "weeks=4"]
        for q in ("진도율", "수료율", "활성화", "주간리텐션", "과제제출률", "정답률추이"):
            r = run([m, "run", q, *common], self.ws, self.env)
            self.assertEqual(r.returncode, 0, f"{q}: {r.stderr}")
            self.assertIn("| ", r.stdout)
        r = run([m, "run", "진도율", "--db", str(db)], self.ws, self.env)
        self.assertNotEqual(r.returncode, 0, "파라미터 누락은 실패해야 함")

    def test_effect_size_and_compare(self):
        m = self.ws / "automation/scripts/metrics.py"
        csv_file = self.tmp / "es.csv"
        rows = ["group,score"] + [f"실험,{60 + i % 5}" for i in range(30)] + [f"대조,{55 + i % 5}" for i in range(30)]
        csv_file.write_text("\n".join(rows), encoding="utf-8")
        r = run([m, "effect-size", "--csv", csv_file, "--group", "group", "--value", "score", "--treat", "실험"], self.ws, self.env)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("d = ", r.stdout)
        r = run([m, "compare", "--metric", "M-01", "--baseline", "52", "--target", "24", "--actual", "20", "--lower-is-better"], self.ws, self.env)
        self.assertIn("| 예 |", r.stdout)


if __name__ == "__main__":
    unittest.main()
