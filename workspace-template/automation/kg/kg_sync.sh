#!/usr/bin/env bash
# 교육과정 지식그래프 원천 저장소 받기
# 사용: automation/kg/kg_sync.sh            # sources.lock.json의 고정 커밋으로 받기
#       automation/kg/kg_sync.sh --check    # 원격 최신 커밋과 비교만
#       automation/kg/kg_sync.sh --update   # 최신 커밋으로 받고 lock 갱신 (갱신 후 kg_build 다시 실행, 변경 사항 확인 후 커밋)
# 받은 저장소의 코드는 실행하지 않는다. kg_build.py가 JSON 데이터만 읽는다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOCK="$ROOT/automation/kg/sources.lock.json"
DEST="$ROOT/data/curriculum-kg/src"
MODE="${1:-}"
mkdir -p "$DEST"

keys=$(python3 -I -c "import json,sys;[print(s['key'],s['repo'],s['commit']) for s in json.load(open(sys.argv[1]))['sources']]" "$LOCK")

while read -r key repo commit; do
  dir="$DEST/$key"
  remote_head=$(git ls-remote "$repo" HEAD | cut -f1)
  if [[ "$MODE" == "--check" ]]; then
    if [[ "$remote_head" == "$commit" ]]; then echo "$key: 최신 ($commit)"; else echo "$key: 새 커밋 있음 (고정 $commit -> 원격 $remote_head)"; fi
    continue
  fi
  target="$commit"
  [[ "$MODE" == "--update" ]] && target="$remote_head"
  if [[ ! -d "$dir/.git" ]]; then
    git init -q "$dir"
    git -C "$dir" remote add origin "$repo"
  fi
  git -C "$dir" fetch -q --depth 1 origin "$target"
  git -C "$dir" checkout -q --detach FETCH_HEAD
  echo "$key: $(git -C "$dir" rev-parse --short HEAD) 받음 -> $dir"
  if [[ "$MODE" == "--update" && "$target" != "$commit" ]]; then
    python3 -I - "$LOCK" "$key" "$target" "$(git -C "$dir" log -1 --format=%cs)" <<'PY'
import json,sys
p,key,c,d=sys.argv[1:5]; j=json.load(open(p,encoding='utf-8'))
for s in j['sources']:
    if s['key']==key: s['commit'],s['commitDate']=c,d
json.dump(j,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
PY
    echo "  lock 갱신: $key -> $target (release 필드는 저장소 CHANGELOG를 보고 직접 고치세요)"
  fi
done <<< "$keys"

[[ "$MODE" == "--check" ]] || echo "다음: python3 automation/kg/kg_build.py"
