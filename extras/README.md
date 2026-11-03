# 선택 설치 (extras)

EdPM은 스킬 33종과 워크스페이스 스크립트만으로 동작합니다. 아래는 산출물을 다른 형식으로 내보내거나 화면을 그릴 때 **선택해서** 쓰는 도구입니다. 없으면 마크다운 산출물만 나옵니다.

## 1. 스킬 없이 되는 것 — 워크스페이스에 포함

| 하는 일 | 도구 | 필요한 것 |
|---------|------|-----------|
| 산출물 → 인쇄용 HTML (표지·목차·표·쪽 번호, 템플릿 예시 행 제거) | `python3 automation/scripts/edpm_export.py <md>` | 없음 |
| 산출물 → PDF | `edpm_export.py <md> --to pdf` | Chrome 또는 Chromium (없으면 HTML을 브라우저에서 "PDF로 저장") |
| 산출물 → Word | `edpm_export.py <md> --to docx [--reference 회사양식.docx]` | [pandoc](https://pandoc.org) (`brew install pandoc`) |
| 클릭 프로토타입 | `06.prototypes/_starter/click-prototype.html` | 브라우저 |
| AI 모델·프롬프트 평가 | `/edpm-eval` (`automation/scripts/ai_eval.py`, 골든셋·시나리오셋) | Claude API 키 또는 로컬 모델 |

회사 문서 양식에 맞춘 출력은 `/edpm-template apply <ID>` → `edpm_export.py`로 냅니다.

## 2. `./install.sh --extras`가 설치하는 것

```bash
./install.sh --extras                                  # 추가 스킬만 설치 (이미 있으면 건너뜀)
./install.sh ~/Work/우리회사-edpm --with-extras         # 워크스페이스 설치와 함께
```

| 스킬 | 하는 일 | EdPM에서 쓰는 곳 | 받는 곳 |
|------|---------|------------------|---------|
| `sb-lowfi-pptx` | 화면설계서(.md, ASCII 와이어프레임) → low-fi 와이어프레임 HTML·편집 가능한 PPTX | E10 화면정보구조 → P0 화면 와이어프레임 | 공개 저장소 [rey-hailey/sb-lowfi](https://github.com/rey-hailey/sb-lowfi) (수동: `/plugin marketplace add rey-hailey/sb-lowfi` → `/plugin install sb-lowfi@sb-lowfi`) |
| `sb-lowfi-figma` | low-fi HTML → Figma 화면설계서 | E10을 Figma로 공유할 때 | 같은 저장소 (Figma MCP 연결 필요) |

`~/.claude/skills/`(사용자 전역)에 설치되어 모든 워크스페이스에서 씁니다.

## 3. 공식 스킬 (원하면)

| 스킬 | 받는 곳 | 쓰는 곳 |
|------|---------|---------|
| `docx`, `pptx`, `xlsx`, `pdf` | Claude Code에서 `/plugin marketplace add anthropics/skills` → `/plugin install document-skills@anthropic-agent-skills` | 발표 자료(pptx), 표 계산 결과(xlsx), 세밀한 Word 편집 |
| `webapp-testing` | 같은 마켓플레이스의 `example-skills@anthropic-agent-skills` | `/edpm-qa run --auto` 화면 E2E (Playwright) |
| `n8n-*` | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) | 회사가 n8n을 쓸 때만 ([guide/04](../guide/04.자동화레이어선택.md)) |

이 저장소에는 제3자 스킬을 넣지 않습니다. 위 링크에서 각자 받습니다.
