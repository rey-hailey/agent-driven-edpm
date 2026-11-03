#!/usr/bin/env bash
# Aside 레시피 실행기
# 사용: automation/scripts/aside-run.sh automation/aside/recipes/R03_교육정책공지모니터링.md [--dry-run]
#
# 레시피의 ```aside 블록을 꺼내 {OUT}을 00.inbox 경로로 바꾸고 `aside "<지시문>"`으로 실행한다.
# Aside가 파일을 직접 저장하지 못하면(파일 접근 권한 설정에 따라 다름) 표준 출력을 같은 경로에 저장한다.
# 확인 필요: Aside CLI의 표준 출력 형식은 공식 문서에 명시돼 있지 않다. 처음 실행 후 결과를 보고 조정한다.
set -euo pipefail

RECIPE="${1:-}"
DRY_RUN="${2:-}"
if [[ -z "$RECIPE" || ! -f "$RECIPE" ]]; then
  echo "사용: $0 <레시피 파일> [--dry-run]" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RID="$(sed -n 's/^id:[[:space:]]*\([A-Za-z0-9]*\).*/\1/p' "$RECIPE" | head -1)"
PII="$(sed -n 's/^pii_risk:[[:space:]]*\([a-z]*\).*/\1/p' "$RECIPE" | head -1)"

if [[ "$PII" == "high" ]]; then
  echo "중단: pii_risk가 high인 레시피는 실행하지 않습니다 ($RECIPE)" >&2
  exit 2
fi

TASK="$(awk '/^```aside/{f=1;next} /^```/{if(f){exit}} f' "$RECIPE")"
if [[ -z "$TASK" ]]; then
  echo "중단: 레시피에 \`\`\`aside 블록이 없습니다" >&2
  exit 1
fi

# {OUT} 외에 채우지 않은 자리표시자가 남아 있으면 중단
LEFT="$(printf '%s' "$TASK" | grep -o '{[^}]*}' | grep -v '^{OUT}$' || true)"
if [[ -n "$LEFT" ]]; then
  echo "중단: 채우지 않은 자리표시자가 있습니다. 레시피를 먼저 채우세요:" >&2
  printf '%s\n' "$LEFT" | sort -u >&2
  exit 3
fi

mkdir -p "$ROOT/00.inbox"
OUT="$ROOT/00.inbox/${RID}_$(date +%Y%m%d_%H%M).md"
TASK="${TASK//\{OUT\}/$OUT}"

if [[ "$DRY_RUN" == "--dry-run" ]]; then
  echo "[dry-run] 출력 경로: $OUT"
  echo "[dry-run] Aside 지시문:"
  printf '%s\n' "$TASK"
  exit 0
fi

if ! command -v aside >/dev/null 2>&1; then
  echo "Aside CLI가 없습니다. 설치: https://docs.aside.com/help/developers" >&2
  echo "레시피의 '수동 대체' 절차를 따르세요." >&2
  exit 4
fi

LOG="$ROOT/00.inbox/.${RID}_$(date +%Y%m%d_%H%M).log"
aside "$TASK" | tee "$LOG"

if [[ ! -s "$OUT" ]]; then
  {
    echo "<!-- Aside가 파일을 직접 저장하지 않아 표준 출력을 저장함. 레시피: $RECIPE -->"
    cat "$LOG"
  } > "$OUT"
fi
echo
echo "저장: $OUT"
echo "다음: /edpm-ingest $OUT"
