#!/usr/bin/env bash
# EdPM Framework 설치: 회사·제품 워크스페이스 만들기
#
# 사용:
#   ./install.sh                         처음이면 이것만: 몇 가지를 묻고 알맞게 설치 (대화형)
#   ./install.sh ~/Work/우리회사-edpm
#   ./install.sh ~/Work/우리회사-edpm --archetype AT01,AT02 --brain ~/EdTech-Brain --with-kg
#
# 옵션:
#   --mode N|F|NF            업무 모드 (N 신사업, F 운영 개선, NF 둘 다)를 AGENTS.md에 기록
#   --archetype AT0x[,AT0y]  서비스 유형을 AGENTS.md에 미리 기록 (적용은 Claude Code에서 /edpm-start blueprint apply)
#   --brain <경로>           개인 EdTech Brain 위치 (기본 ~/EdTech-Brain, 없으면 brain-seed로 새로 만듦)
#   --with-kg                국가 교육과정 지식그래프를 받아 빌드 (약 260MB 다운로드, git·python3 필요)
#   --dev team|vibe          개발 체계 (team: 개발팀이 있음 — PM은 스펙까지, vibe: 개발자 없이 PM이 LLM과 구현)
#   --no-git                 git init 하지 않음
#   --no-sb-lowfi            화면설계 스킬 sb-lowfi 설치를 건너뜀 (기본: ~/.claude/skills에 함께 설치, 이미 있으면 건너뜀)
#   ./install.sh --check     설치 없이 필수 도구·외부 스킬만 점검 (guide/00.시작하기.md)
#   ./install.sh --extras    sb-lowfi만 설치 (설치 때 네트워크가 없었을 때, extras/README.md)
#   ./install.sh --upgrade <워크스페이스>  스킬·스크립트·훅·설정을 새 버전으로 (작성한 산출물·위키는 그대로)
set -euo pipefail

FW="$(cd "$(dirname "$0")" && pwd)"

# EdPM과 함께 쓰는 화면설계 스킬(sb-lowfi)을 사용자 전역에 설치한다. 워크스페이스 설치·업그레이드 때 기본으로 실행. 이미 있는 스킬은 덮어쓰지 않는다.
# Word·PDF 출력은 스킬 없이 워크스페이스의 automation/scripts/edpm_export.py가 맡는다.
install_extras() {
  local dest="$HOME/.claude/skills"
  mkdir -p "$dest"
  echo "[화면설계 스킬 sb-lowfi → $dest]"
  install_sb_lowfi "$dest"
  echo "  안내: extras/README.md (Word·PDF 출력은 edpm_export.py, 공식 문서 스킬은 선택)"; return 0
}

# sb-lowfi-pptx·sb-lowfi-figma는 별도 공개 저장소에서 받는다. 이미 있으면 건너뛴다.
SB_LOWFI_REPO="https://github.com/rey-hailey/sb-lowfi.git"
install_sb_lowfi() {
  local dest="$1" tmp s need=0
  for s in sb-lowfi-pptx sb-lowfi-figma; do [[ -e "$dest/$s" ]] || need=1; done
  if [[ $need -eq 0 ]]; then echo "  = sb-lowfi-pptx, sb-lowfi-figma 이미 있음, 건너뜀"; return 0; fi
  tmp=$(mktemp -d)
  if git clone -q --depth 1 "$SB_LOWFI_REPO" "$tmp/sb-lowfi" 2>/dev/null; then
    for s in sb-lowfi-pptx sb-lowfi-figma; do
      if [[ -e "$dest/$s" ]]; then echo "  = $s 이미 있음, 건너뜀"
      else cp -R "$tmp/sb-lowfi/plugins/sb-lowfi/skills/$s" "$dest/$s" && echo "  + $s (rey-hailey/sb-lowfi)"; fi
    done
  else
    echo "  – sb-lowfi 저장소를 받지 못함 (네트워크 확인). Claude Code에서 직접 설치:"
    echo "      /plugin marketplace add rey-hailey/sb-lowfi"
    echo "      /plugin install sb-lowfi@sb-lowfi"
  fi
  rm -rf "$tmp"
}

# 사전 점검: 필수 도구가 없으면 1을 돌려준다. 외부 스킬은 안내만 한다.
preflight() {
  local ws="${1:-}" missing=0 v
  echo "[필수 도구]"
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
    echo "  ✓ python3 $(python3 -c 'import platform; print(platform.python_version())')"
  else
    echo "  ✗ python3 3.9 이상 필요 (macOS: xcode-select --install 또는 brew install python)"; missing=1
  fi
  if command -v git >/dev/null 2>&1; then echo "  ✓ git"; else echo "  ✗ git 필요 (macOS: xcode-select --install)"; missing=1; fi
  if command -v claude >/dev/null 2>&1; then
    v=$(claude --version 2>/dev/null | head -1 || true); echo "  ✓ Claude Code ${v}"
  else
    echo "  ✗ Claude Code 필요 — https://claude.com/claude-code (설치는 계속되지만 스킬을 실행할 수 없음)"
  fi
  echo "[함께 쓰는 스킬]"
  local plugins="$HOME/.claude/plugins/installed_plugins.json" s found
  for s in docx pptx xlsx pdf webapp-testing sb-lowfi-pptx sb-lowfi-figma; do
    found=""
    [[ -f "$HOME/.claude/skills/$s/SKILL.md" ]] && found="~/.claude/skills"
    [[ -z "$found" && -n "$ws" && -f "$ws/.claude/skills/$s/SKILL.md" ]] && found="워크스페이스"
    if [[ -z "$found" && -f "$plugins" ]]; then
      case "$s" in
        docx|pptx|xlsx|pdf) grep -q '"document-skills@' "$plugins" && found="document-skills 플러그인" ;;
        webapp-testing) grep -q '"example-skills@' "$plugins" && found="example-skills 플러그인" ;;
        sb-lowfi-pptx|sb-lowfi-figma) grep -q '"sb-lowfi@' "$plugins" && found="sb-lowfi 플러그인" ;;
      esac
    fi
    if [[ -n "$found" ]]; then echo "  ✓ $s ($found)"; else echo "  – $s 없음"; fi
  done
  echo "  Word·PDF는 스킬 없이 edpm_export.py가 만듭니다(PDF: Chrome, Word: pandoc). sb-lowfi: 워크스페이스 설치 때 자동(없으면 ./install.sh --extras), 공식 docx·pptx·xlsx·pdf·webapp-testing(선택): guide/00.시작하기.md 3.2절"
  command -v pandoc >/dev/null 2>&1 && echo "  ✓ pandoc (Word 출력)" || echo "  – pandoc 없음 (Word 출력용, 선택: brew install pandoc)"
  echo "[선택 도구]"
  command -v obsidian >/dev/null 2>&1 || [[ -d /Applications/Obsidian.app ]] && echo "  ✓ Obsidian" || echo "  – Obsidian 없음 (위키 보기용, 없어도 동작)"
  command -v aside >/dev/null 2>&1 && echo "  ✓ Aside CLI" || echo "  – Aside CLI 없음 (/edpm-wiki collect 웹 수집용)"
  python3 -c 'import anthropic' 2>/dev/null && echo "  ✓ anthropic 패키지" || echo "  – anthropic 패키지 없음 (/edpm-ai eval Claude 평가용: pip install anthropic)"
  if command -v gh >/dev/null 2>&1; then
    gh auth status >/dev/null 2>&1 && echo "  ✓ GitHub CLI (로그인됨)" || echo "  – GitHub CLI 로그인 필요: gh auth login (WBS를 GitHub로 공유할 때)"
  else
    echo "  – GitHub CLI 없음 (WBS를 GitHub 이슈로 공유할 때: brew install gh)"
  fi
  if command -v node >/dev/null 2>&1 && node -e 'process.exit(parseInt(process.versions.node) >= 20 ? 0 : 1)' 2>/dev/null; then
    echo "  ✓ Node.js $(node --version)"
  else
    echo "  – Node.js 20 이상 없음 (코드 MVP 프로토타입·pptx 스킬용: brew install node)"
  fi
  return $missing
}

TARGET="${1:-}"
if [[ "$TARGET" == "--check" ]]; then preflight; exit $?; fi
if [[ "$TARGET" == "--extras" ]]; then install_extras; exit 0; fi
if [[ "$TARGET" == "--upgrade" ]]; then
  WS="${2:-}"; [[ -d "$WS/.claude" && -f "$WS/AGENTS.md" ]] || { echo "사용: ./install.sh --upgrade <워크스페이스 경로>" >&2; exit 1; }
  echo "[업그레이드] $WS"
  rm -rf "$WS"/.claude/skills/edpm-*/   # 프레임워크 스킬만 제거 (사용자가 추가한 다른 스킬은 보존)
  rsync -a "$FW/workspace-template/.claude/skills/" "$WS/.claude/skills/" && echo "  스킬 $(ls -d "$WS"/.claude/skills/edpm-*/ | wc -l | tr -d ' ')종 갱신"
  rsync -a "$FW/workspace-template/automation/scripts/" "$WS/automation/scripts/" && echo "  automation/scripts 갱신"
  rsync -a "$FW/workspace-template/automation/hooks/" "$WS/automation/hooks/" && echo "  automation/hooks 갱신"
  mkdir -p "$WS/.edpm" && rsync -a --delete "$FW/library/" "$WS/.edpm/library/" && echo "  보관함 .edpm/library 갱신 (꺼내 쓴 산출물은 그대로)"
  [[ " $* " == *" --no-sb-lowfi "* ]] || { mkdir -p "$HOME/.claude/skills"; install_sb_lowfi "$HOME/.claude/skills"; }
  rsync -a "$FW/workspace-template/automation/kg/" --exclude sources.lock.json "$WS/automation/kg/" 2>/dev/null || true
  rsync -a --ignore-existing "$FW/workspace-template/automation/sql/" "$WS/automation/sql/" && echo "  automation/sql 템플릿 추가 (기존 파일 유지)"
  rsync -a --ignore-existing "$FW/workspace-template/.github/" "$WS/.github/" 2>/dev/null || true
  if [[ -f "$WS/.claude/settings.json" ]]; then
    cmp -s "$FW/workspace-template/.claude/settings.json" "$WS/.claude/settings.json" || { cp "$FW/workspace-template/.claude/settings.json" "$WS/.claude/settings.new.json"; echo "  .claude/settings.json 이 다릅니다 → settings.new.json 으로 두었습니다. 비교 후 합치세요"; }
  else
    cp "$FW/workspace-template/.claude/settings.json" "$WS/.claude/settings.json" && echo "  .claude/settings.json 추가 (훅·권한)"
  fi
  # 원점 PRD와 제품 코드 폴더 (없을 때만)
  [[ -d "$WS/templates/회사양식" ]] || { mkdir -p "$WS/templates" && cp -R "$FW/workspace-template/templates/회사양식" "$WS/templates/" && echo "  + templates/회사양식/ (회사 문서 양식 연결 — /edpm-template)"; }
  [[ -e "$WS/PRD.md" ]] || { cp "$FW/workspace-template/PRD.md" "$WS/PRD.md" && echo "  + PRD.md (원점 문서 — /edpm-prd 로 작성. G-PRD: review 이상이어야 다른 산출물 완료 가능)"; }
  [[ -e "$WS/src/README.md" ]] || { mkdir -p "$WS/src" && cp "$FW/workspace-template/src/README.md" "$WS/src/README.md" && echo "  + src/ (제품 코드, 스펙 승인 후 — G-SPEC)"; }
  # 새 템플릿·변경된 템플릿 안내 (산출물은 덮어쓰지 않음)
  new=0; changed=0
  while IFS= read -r -d '' f; do
    rel="${f#$FW/workspace-template/}"
    if [[ ! -e "$WS/$rel" ]]; then
      if [[ "$rel" == *"/_"*템플릿*/* || "$rel" == *.csv || "$rel" == 06.prototypes/* ]]; then
        mkdir -p "$WS/$(dirname "$rel")"; cp "$f" "$WS/$rel"; echo "  + $rel"
      else
        new=$((new+1)); echo "  새 핵심 템플릿 (복사 안 함, 필요하면 직접 복사): $rel"
      fi
    elif ! cmp -s "$f" "$WS/$rel"; then changed=$((changed+1)); fi
  done < <(find "$FW/workspace-template/03.docs" "$FW/workspace-template/06.prototypes" "$FW/workspace-template/04.ops" "$FW/workspace-template/02.wiki/decisions" -type f -print0)
  echo "  템플릿이 바뀐 산출물 $changed건 (작성 중인 문서라 덮어쓰지 않음). 변경 내용은 CHANGELOG.md 참고"
  echo "  AGENTS.md 는 사람이 관리합니다. 새 절(스킬 표·하네스)은 CHANGELOG 를 보고 옮기세요: diff "$FW/workspace-template/AGENTS.md" "$WS/AGENTS.md""
  exit 0
fi
# 대화형 설치: 인자 없이 터미널에서 실행하면 몇 가지를 묻는다
if [[ -z "$TARGET" && ( -t 0 || -n "${EDPM_WIZARD:-}" ) ]]; then   # EDPM_WIZARD=1: 시험용 강제
  echo "EdPM 워크스페이스를 만듭니다. 모르면 Enter (기본값)."
  echo
  read -r -p "1) 회사·제품 이름 (폴더 이름에 씀) [우리회사]: " name; name="${name:-우리회사}"
  def_path="$HOME/Work/${name}-edpm"
  read -r -p "2) 만들 위치 [$def_path]: " path; path="${path:-$def_path}"; path="${path/#\~/$HOME}"
  echo "3) 어떤 일을 하시나요?"
  echo "   1 새 서비스·신사업을 시작한다 (N)   2 운영 중인 서비스를 개선한다 (F)   3 둘 다 (NF)"
  read -r -p "   선택 [1]: " m; case "${m:-1}" in 2) m=F ;; 3) m=NF ;; *) m=N ;; esac
  echo "4) 제품은 누가 만드나요?"
  echo "   1 개발팀이 있다 (PM은 PRD·스펙·프로토타입까지)   2 개발자 없이 직접 만든다 (바이브코딩)"
  read -r -p "   선택 [1]: " dv; if [[ "${dv:-1}" == 2 ]]; then dv=vibe; else dv=team; fi
  set -- "$path" --mode "$m" --dev "$dv"
  TARGET="$1"
  echo; echo "실행: ./install.sh $*"; echo
fi
[[ -z "$TARGET" || "$TARGET" == --* ]] && { sed -n '2,21p' "$0"; exit 1; }
shift
MODE=""; ARCH=""; DEV=""; BRAIN="$HOME/EdTech-Brain"; WITH_KG=0; GIT=1; EXTRAS=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --archetype) ARCH="$2"; shift 2 ;;
    --dev) DEV="$2"; shift 2 ;;
    --brain) BRAIN="$2"; shift 2 ;;
    --with-kg) WITH_KG=1; shift ;;
    --no-git) GIT=0; shift ;;
    --with-extras) EXTRAS=1; shift ;;   # 예전 옵션: 이제 기본
    --no-sb-lowfi) EXTRAS=0; shift ;;
    *) echo "알 수 없는 옵션: $1" >&2; exit 1 ;;
  esac
done

if [[ -e "$TARGET" && -n "$(ls -A "$TARGET" 2>/dev/null)" ]]; then
  echo "중단: $TARGET 가 비어 있지 않습니다. 기존 워크스페이스를 덮어쓰지 않습니다." >&2
  exit 2
fi

if [[ -n "$ARCH" ]]; then
  for a in ${ARCH//,/ }; do
    ls "$FW/archetypes/${a}_"*.md >/dev/null 2>&1 || { echo "중단: 서비스 유형 $a 를 찾을 수 없습니다 (archetypes/ 참고)" >&2; exit 3; }
  done
fi

[[ $EXTRAS -eq 1 ]] && { install_extras; echo; }

preflight || { echo "중단: 필수 도구를 먼저 설치하세요 (guide/00.시작하기.md 2절)" >&2; exit 4; }
echo

# 1) 워크스페이스
mkdir -p "$TARGET"
cp -R "$FW/workspace-template/." "$TARGET/"
mkdir -p "$TARGET/.edpm" && cp -R "$FW/library" "$TARGET/.edpm/library"
echo "워크스페이스 생성: $TARGET (핵심 경로 산출물만. 나머지 $(find "$TARGET/.edpm/library" -name '*.md' -not -path '*/_*' | wc -l | tr -d ' ')종은 보관함 .edpm/library — /edpm-doc <ID>가 필요할 때 꺼냄)"
echo "EdPM 스킬 $(ls -d "$TARGET"/.claude/skills/edpm-*/ | wc -l | tr -d ' ')종 설치: $TARGET/.claude/skills/ (이 폴더에서 claude를 열면 /edpm-* 로 보임)"

# 2) 개인 Brain
if [[ ! -d "$BRAIN" ]]; then
  cp -R "$FW/brain-seed" "$BRAIN"
  echo "개인 Brain 생성: $BRAIN (회사 기밀을 넣지 않는 개인 저장소로 관리하세요)"
else
  echo "개인 Brain 사용: $BRAIN"
fi

# 3) 도메인 지식 시드 (이미 있는 파일은 덮어쓰지 않음)
mkdir -p "$TARGET/02.wiki/domain"
cp -Rn "$BRAIN/domain/." "$TARGET/02.wiki/domain/" 2>/dev/null || true
echo "도메인 지식 시드: $(ls "$TARGET/02.wiki/domain" | grep -c '\.md$')개 페이지"

# 4) AGENTS.md에 경로·유형 기록
python3 - "$TARGET/AGENTS.md" "$FW" "$BRAIN" "$ARCH" "$MODE" "$DEV" <<'PY'
import sys, re
p, fw, brain, arch, mode, dev = sys.argv[1:7]
s = open(p, encoding="utf-8").read()
s = re.sub(r"^\| 프레임워크 경로 \|.*$", f"| 프레임워크 경로 | {fw} — 가이드 원문(`guide/`)·서비스 유형(`archetypes/`) 참조용 |", s, count=1, flags=re.M)
s = re.sub(r"^\| 개인 Brain 경로 \|.*$", f"| 개인 Brain 경로 | {brain} |", s, count=1, flags=re.M)
if arch:
    s = re.sub(r"^\| 서비스 유형 \|.*$", f"| 서비스 유형 | {arch} (설치 시 지정, `/edpm-start blueprint apply {arch}`로 적용) |", s, count=1, flags=re.M)
names = {"N": "N 신사업(0→1)", "F": "F 운영 개선(1→n)", "NF": "둘 다 (N 신사업 + F 운영 개선)"}
if mode:
    s = re.sub(r"^\| 업무 모드 \|.*$", f"| 업무 모드 | {names.get(mode.upper(), mode)} (설치 시 지정) — `guide/09.업무모드.md` |", s, count=1, flags=re.M)
devs = {"team": "개발팀 (PM은 PRD·스펙·프로토타입까지, 제품 코드는 개발팀)", "vibe": "바이브코딩 (개발자 없이 PM이 LLM과 구현, 스펙 승인 후 src/)"}
if dev:
    s = re.sub(r"^\| 개발 체계 \|.*$", f"| 개발 체계 | {devs.get(dev, dev)} (설치 시 지정) |", s, count=1, flags=re.M)
open(p, "w", encoding="utf-8").write(s)
PY

# 4.0) 업무 모드에 맞는 산출물 꺼내기 (신사업 N01·N03·N04, 운영 개선 F00·백로그·과제 템플릿)
case "$MODE" in *N*|*n*) EDPM_ROOT="$TARGET" python3 "$TARGET/automation/scripts/edpm_check.py" add N01 N03 N04 | sed 's/^/  /' ;; esac
case "$MODE" in *F*|*f*) EDPM_ROOT="$TARGET" python3 "$TARGET/automation/scripts/edpm_check.py" add F00 | sed 's/^/  /' ;; esac

# 4.1) 서비스 유형 프로필 사본 (워크스페이스 위키에서 참조)
if [[ -n "$ARCH" ]]; then
  mkdir -p "$TARGET/02.wiki/company"
  for a in ${ARCH//,/ }; do
    src=$(ls "$FW/archetypes/${a}_"*.md | head -1)
    dst="$TARGET/02.wiki/company/서비스유형_$(basename "$src")"
    # 선택한 유형끼리는 위키 링크, 선택하지 않은 유형은 프레임워크 경로 텍스트 (끊긴 링크 방지)
    python3 - "$src" "$dst" "$ARCH" <<'PY2'
import re, sys
src, dst, arch = sys.argv[1:4]
chosen = set(arch.split(","))
s = open(src, encoding="utf-8").read()
def sub(m):
    name = m.group(1)
    return f"[[company/서비스유형_{name}]]" if name.split("_")[0] in chosen else f"`archetypes/{name}.md`(프레임워크)"
s = re.sub(r"\[\[archetypes/([^\]|]+)(?:\|[^\]]*)?\]\]", sub, s)
open(dst, "w", encoding="utf-8").write(s)
PY2
  done
  echo "서비스 유형 프로필 복사: $ARCH → 02.wiki/company/"
fi

# 5) git
if [[ $GIT -eq 1 ]] && command -v git >/dev/null 2>&1; then
  git -C "$TARGET" init -q && echo "git 저장소 초기화 (00.inbox, data/curriculum-kg, 비밀 파일은 .gitignore로 제외)"
fi

# 6) 교육과정 지식그래프 (선택)
if [[ $WITH_KG -eq 1 ]]; then
  ( cd "$TARGET" && automation/kg/kg_sync.sh && python3 automation/kg/kg_build.py )
fi

cat <<EOF

시작하기:
  cd "$TARGET" && claude
  세션이 열리면 상황판이 "지금 단계"와 다음 할 일을 알려줍니다. 처음이면 /edpm-start 를 입력하세요.
  순서: /edpm-start → /edpm-start init (회사·제품 인터뷰) → /edpm-prd (만들 제품 전체 정의) → 상황판이 안내하는 다음 단계
  자세한 길잡이: $FW/guide/14.AtoZ사용가이드.md
Obsidian에서 "$TARGET" 폴더를 볼트로 열면 위키와 산출물을 함께 볼 수 있습니다.
EOF
