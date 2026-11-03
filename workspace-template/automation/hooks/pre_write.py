#!/usr/bin/env python3
"""Claude Code PreToolUse 훅 (Write|Edit). 워크스페이스 규칙을 문장이 아니라 장치로 지킨다.

막는 것 (exit 2 → 도구 실행 취소, stderr가 Claude에게 전달됨):
  1. 01.자료실/ 기존 파일 수정 (추가만 허용, _자료목록.md·README.md 제외)        — AGENTS.md 3절
  2. 03.docs/ 산출물을 status: done 으로 바꾸는데 전제조건·게이트 미충족, gate_skip 없음 — AGENTS.md 6절
  3. 01.자료실/·02.wiki/ 에 휴대전화·주민등록번호·이메일 패턴 쓰기                 — G-PII
  4. src/ 제품 코드 쓰기: PRD가 review 이상이고 스펙(E09)이 done일 때만, 개발 체계가 '개발팀'이면 차단 — G-PRD·G-SPEC
  5. 생성 게이트: 03.docs/·PRD.md 산출물의 본문을 전제조건(+G-PRD)이 끝나기 전에 쓰기 — A가 끝나야 B
     (frontmatter만 바꾸기, n/a 처리, gate_skip·early_draft 사유는 통과)
  6. PRD를 review로 올리는데 명확도 미달 (모호도 > 0.3)                                  — G-CLEAR
  7. holdout 평가셋(파일 이름에 holdout)을 읽기·검색·수정 — 점수는 ai_eval.py --holdout으로만     — 숨긴 채점 기준
  8. 커밋된 인수조건 테스트(tests/) 수정 — 스펙을 먼저 고치고 .edpm/test-unlock에 경로·사유      — 테스트 고정
그 밖의 경우는 exit 0 (통과). 훅이 오류를 내면 통과시킨다 (작업을 막는 것보다 안전).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
CHECK = ROOT / "automation" / "scripts" / "edpm_check.py"


def _tracked(rel: Path) -> bool:
    """git HEAD에 커밋된 파일인가 (git 저장소가 아니면 False)."""
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"HEAD:{rel.as_posix()}"], capture_output=True)
        return r.returncode == 0
    except Exception:
        return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {}) or {}
    fp = inp.get("file_path") or ""

    # 7) holdout 평가셋은 보지 않는다: 보면 그 문항에 맞춰 프롬프트를 고치게 되어 점수가 실제 품질을 말하지 않는다
    HOLD = "차단 (holdout): 이 평가셋은 프롬프트를 고치는 쪽이 보지 않는 세트입니다. 점수만 `python3 automation/scripts/ai_eval.py --set <holdout 파일> --system <프롬프트> --holdout`으로 확인합니다 (문항·답은 출력되지 않음)."
    if tool == "Bash":
        cmd = inp.get("command") or ""
        if "holdout" in cmd.lower() and "ai_eval.py" not in cmd:
            print(HOLD, file=sys.stderr)
            return 2
        return 0
    if tool in {"Read", "Grep"}:
        target = fp or inp.get("path") or ""
        if "holdout" in Path(target).name.lower() or "holdout" in (inp.get("glob") or "").lower():
            print(HOLD, file=sys.stderr)
            return 2
        return 0
    if tool not in {"Write", "Edit", "MultiEdit"} or not fp:
        return 0
    path = Path(fp)
    if not path.is_absolute():
        path = ROOT / path
    try:
        rel = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return 0
    top = rel.parts[0] if rel.parts else ""
    new_text = inp.get("content") or inp.get("new_string") or ""
    if tool == "MultiEdit":
        new_text = "\n".join(e.get("new_string", "") for e in inp.get("edits", []))

    if "holdout" in path.name.lower() and path.exists():
        print(HOLD + " 세트를 바꾸려면 사람이 직접 고칩니다.", file=sys.stderr)
        return 2

    # 8) 인수조건 테스트 고정: 커밋된 테스트를 구현 중에 고치면 테스트가 구현을 따라가게 된다
    if top == "tests" and path.exists() and _tracked(rel):
        unlock = ROOT / ".edpm" / "test-unlock"
        allowed = unlock.exists() and any(ln.split("|")[0].strip() == str(rel) for ln in unlock.read_text(encoding="utf-8").splitlines())
        if not allowed:
            print(f"차단 (테스트 고정): {rel}은 커밋된 인수조건 테스트입니다. 구현에 맞춰 테스트를 고치지 않습니다. "
                  "인수조건 자체가 바뀌었다면 스펙(E09·F02)의 AC를 먼저 고치고, 사용자 확인 후 `.edpm/test-unlock`에 "
                  f"`{rel} | 사유 | YYYY-MM-DD` 한 줄을 추가한 뒤 다시 저장합니다 (상황판에 표시됨).", file=sys.stderr)
            return 2

    # 1) 자료실은 추가만
    if top == "01.자료실" and path.exists() and path.name not in {"_자료목록.md", "README.md", ".gitkeep"}:
        print(f"차단: 01.자료실의 기존 파일은 수정하지 않습니다 ({rel}). 정정이 필요하면 새 파일로 추가하고 원본은 그대로 둡니다 (AGENTS.md 3절).", file=sys.stderr)
        return 2

    # 3) 개인정보
    if top in {"01.자료실", "02.wiki"} and new_text:
        r = subprocess.run([sys.executable, str(CHECK), "pii", "/dev/stdin"], input=new_text, capture_output=True, text=True,
                           env={**os.environ, "EDPM_ROOT": str(ROOT)})
        if r.returncode == 1:
            print(f"차단 (G-PII): {r.stdout.strip()} — 실명·연락처·학번은 가명으로 바꾼 뒤 저장합니다 (AGENTS.md 7절). 예시·플레이스홀더면 example.com 또는 {{…}} 형식을 쓰세요.", file=sys.stderr)
            return 2

    # 4) 제품 코드는 스펙 승인 후 (G-SPEC), 개발팀 체계면 PM이 쓰지 않음
    if top == "src" and path.name != "README.md":
        r = subprocess.run([sys.executable, str(CHECK), "code-gate", str(path)], capture_output=True, text=True,
                           env={**os.environ, "EDPM_ROOT": str(ROOT)})
        if r.returncode == 1:
            print(f"차단: {r.stdout.strip()}", file=sys.stderr)
            return 2

    # 5) 생성 게이트: A(전제)가 끝나야 B의 본문을 쓴다. frontmatter만 바꾸는 수정, n/a 처리,
    #    gate_skip·early_draft 사유가 있으면 통과. 템플릿 폴더(_…)는 대상 아님.
    is_doc = (top == "03.docs" or str(rel) == "PRD.md") and path.suffix == ".md" \
        and not any(part.startswith("_") for part in rel.parts)
    if is_doc:
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        if tool == "Write":
            merged = inp.get("content") or ""
        elif tool == "MultiEdit":
            merged = old
            for e in inp.get("edits", []):
                merged = merged.replace(e.get("old_string", ""), e.get("new_string", ""), 1)
        else:
            merged = old.replace(inp.get("old_string", ""), inp.get("new_string", ""), 1)
        body = lambda t: t.split("\n---", 2)[-1] if t.startswith("---") else t  # noqa: E731
        allowed = (body(merged).strip() == body(old).strip()
                   or re.search(r"^status:[ \t]*n/a\b", merged, re.M)
                   or re.search(r"^(gate_skip|early_draft):[ \t]*\S", merged, re.M)
                   or not re.search(r"^doc_id:", merged, re.M))
        if not allowed:
            tmp = path.with_suffix(".edpm-start-check.tmp")
            try:
                tmp.write_text(merged, encoding="utf-8")
                r = subprocess.run([sys.executable, str(CHECK), "start", str(tmp)], capture_output=True, text=True,
                                   env={**os.environ, "EDPM_ROOT": str(ROOT)})
            finally:
                tmp.unlink(missing_ok=True)
            if r.returncode == 1:
                print(f"차단: {r.stdout.strip()}\n전제 산출물을 먼저 진행합니다 (상황판의 지금 단계, `edpm_check.py progress`). "
                      "사용자가 '미리 초안만'을 명시하면 frontmatter에 `early_draft: [사유]`를 적고 다시 저장합니다 — 상황판에 계속 표시됩니다.", file=sys.stderr)
                return 2

    # 6) PRD를 review로 올릴 때 명확도 (G-CLEAR)
    if str(rel) == "PRD.md" and re.search(r"^status:[ \t]*review\b", new_text, re.M):
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        if not re.search(r"^status:[ \t]*(review|done)\b", old, re.M):
            merged = new_text if tool == "Write" else old.replace(inp.get("old_string", ""), new_text, 1)
            if not re.search(r"^gate_skip:[ \t]*\S", merged, re.M):
                tmp = path.with_suffix(".edpm-clarity-check.tmp")
                try:
                    tmp.write_text(merged, encoding="utf-8")
                    r = subprocess.run([sys.executable, str(CHECK), "clarity", str(tmp)], capture_output=True, text=True,
                                       env={**os.environ, "EDPM_ROOT": str(ROOT)})
                finally:
                    tmp.unlink(missing_ok=True)
                if r.returncode == 1:
                    print(f"차단 (G-CLEAR): PRD가 아직 흐립니다. 흐린 채로 스펙·프로토타입으로 가면 엉뚱한 것을 만듭니다.\n{r.stdout.strip()}\n"
                          "빈 곳을 채우거나(리서치·인터뷰), 사용자가 명시적으로 허용하면 `gate_skip: [사유]`를 적고 다시 저장합니다.", file=sys.stderr)
                    return 2

    # 2) done 전환 게이트 (PRD.md 포함)
    if (top == "03.docs" or str(rel) == "PRD.md") and re.search(r"^status:[ \t]*done\b", new_text, re.M):
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        if re.search(r"^status:[ \t]*done\b", old, re.M):
            return 0  # 이미 done인 문서의 다른 수정
        merged = new_text if tool == "Write" else old.replace(inp.get("old_string", ""), new_text, 1)
        if re.search(r"^gate_skip:[ \t]*\S", merged, re.M):
            return 0  # 사유를 남긴 스킵은 허용 (lint가 보고)
        tmp = path.with_suffix(".edpm-gate-check.tmp")
        try:
            tmp.write_text(merged, encoding="utf-8")
            r = subprocess.run([sys.executable, str(CHECK), "gate", str(tmp)], capture_output=True, text=True,
                               env={**os.environ, "EDPM_ROOT": str(ROOT)})
        finally:
            tmp.unlink(missing_ok=True)
        if r.returncode == 1:
            print(f"차단: {r.stdout.strip()}\n전제 산출물을 먼저 완료하거나, 사용자가 명시적으로 허용하면 frontmatter에 `gate_skip: [사유]`를 적고 다시 저장합니다 (AGENTS.md 6절).", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 훅 자체 오류는 작업을 막지 않는다
        print(f"pre_write 훅 오류 (통과 처리): {e}", file=sys.stderr)
        sys.exit(0)
