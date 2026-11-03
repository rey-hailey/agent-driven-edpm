---
name: edpm-brief
description: 지금 상황과 할 일, 그리고 보고를 맡는다. 상황판(점검기 결과 → 오늘 할 일), 진행표, 주간보고(weekly), 관리 보고서 M01 착수·M03 위험·M04 중간·M05 완료·경영진 요약(report), 회의 준비·회의록 → 결정·액션·위키 반영(meeting). "오늘 뭐 해야 해", "상황판", "지금 어디까지 왔어", "다음에 뭐 써", "진행표", "주간보고", "착수보고서", "중간보고", "경영진 보고", "회의 준비", "회의록 정리", "액션 아이템" 요청에 사용. 세션 시작 때는 훅이 상황판 요약을 자동으로 보여준다.
argument-hint: "[week | next | progress | gates | dashboard] | weekly [YYYY-MM-DD] | report <M01 | M03 | M04 | M05 | exec> [--format md|docx|pdf|pptx] | meeting <prep | notes | ingest | actions>"
---

# edpm-brief

1. `python3 automation/scripts/edpm_check.py brief`를 실행합니다 (훅이 세션 시작 때 이미 보여줬으면 다시 실행하지 않고 그 결과를 씁니다).
2. 상황판 첫 절 **"지금 단계"**(PRD → 착수·근거 → 상세 요구사항 → 스펙 → 프로토타입·구현 → 출시)를 맨 위에 그대로 보여줍니다. 이 단계의 다음 할 일이 오늘 할 일의 기본입니다. 단계를 건너뛰는 작업을 하려 하면 왜 순서가 그런지 한 줄로 알립니다.
3. 결과를 **오늘 할 일 3~5개**로 바꿉니다. 우선순위:
   0. 지금 단계의 다음 할 일 (예: PRD가 draft면 `/edpm-prd review`)
   1. 막힌 것 풀기: 게이트 미충족 done, 개인정보 의심, 종료일 지난 WP, timebox 지난 프로토타입
   2. 기다리는 사람이 있는 것: `review` 상태 산출물, 반영 안 된 회의록·액션 아이템, 재검토일 지난 결정
   3. 다음 산출물: 전제조건을 충족한 미완료 산출물 중 업무 모드 흐름상 다음 것 (N: N01→N04, F: F00→F04, 프로토타입 진행 중이면 V 우선)
   4. 시즌: `02.wiki/domain/학사일정.md`와 E00 시즌 캘린더에서 4주 안의 이벤트 (시험·방학·예산 마감)
4. 각 항목에 실행할 명령을 붙입니다 (`/edpm-doc E09`, `/edpm-wbs pull`, `/edpm-decide review ADR-007` …).
5. 묻지 않고 바로 할 수 있는 것(진척 pull, 린트)은 제안만 하고 실행은 승인 후.


## 하위 명령

| 명령 | 읽을 파일 | 하는 일 |
|------|-----------|---------|
| (없음)·`week`·`next`·`progress`·`gates` | 이 파일 | 상황판, 이번 주, 다음 할 일, 진행표, 게이트 |
| `dashboard` | 이 파일 | 대시보드 화면 열기: `python3 automation/scripts/edpm_dashboard.py --open` → `.edpm/dashboard.html` (지금 단계·PRD 명확도·일정·지식 그래프·주의·경로 문서·스킬). 세션 시작과 문서 저장 때 훅이 다시 만들고, 열어 둔 화면은 조용할 때 스스로 새로 읽음. 보기 전용 — 상태는 문서 frontmatter가 기준 |
| `weekly` | `weekly.md` | 주간보고 |
| `report` | `report.md` | 관리 보고서·경영진 요약 (M 문서가 없으면 보관함에서 꺼냄) |
| `meeting` | `meeting.md` | 회의 준비 한 장, 회의록 → ADR·WBS·백로그·ingest |

하위 명령이면 같은 폴더의 해당 파일을 읽고 그 절차를 따릅니다.

## week

`/edpm-brief weekly` 전 주간 점검: 지난 7일 log, 상태 변화, 이번 주 마감 WP, 다음 주 시즌 이벤트. 주간보고 초안 작성으로 이어갈지 묻습니다.

## progress

`edpm_check.py progress`: 진행표 한 장(문서·상태·완료일·전제조건·지금 착수 가능/대기 이유). `--all`이면 해당없음 포함.

## next

`edpm_check.py next`: 전제조건을 충족해 지금 쓸 수 있는 산출물만.

## gates

게이트 미충족 done, 게이트 스킵 목록과 사유, 해소 방법.
