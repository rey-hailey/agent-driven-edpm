---
name: edpm-weekly
description: 주간보고를 만든다. 지난 7일의 위키 log, 산출물 상태 변화, 의사결정, git 커밋, 다가오는 학사 일정을 모아 04.ops/주간보고에 저장한다. 회사 이슈 트래커 내보내기 파일이 있으면 함께 반영한다. "주간보고", "이번 주 정리", "위클리" 요청에 사용.
argument-hint: "[기준일 YYYY-MM-DD, 기본 오늘]"
---

# edpm-weekly

## 절차

1. **기간**: 기준일 D를 정하고 D-6 ~ D를 보고 기간으로 합니다.
2. **자료 모으기**
   - `02.wiki/log.md`에서 기간 안의 항목 (`grep "^## \[" 02.wiki/log.md`로 날짜 필터)
   - `03.docs/` frontmatter의 `updated`가 기간 안인 산출물과 상태
   - `02.wiki/decisions/`에서 기간 안에 만든 ADR, 재검토일이 지난 ADR (`edpm_check.py json`의 `decisions_due` → `/edpm-decide review` 제안)
   - `04.ops/회의록/` 기간 내 회의록과 액션 아이템 (기한 지난 것은 리스크로)
   - 모드 F: `03.docs/F.개선/` 과제 폴더별 F01~F04 상태 변화, 이번 주 출시·효과 리뷰, 백로그 신규 요청 수 (`/edpm-feature status`)
   - 모드 N: 현재 단계와 다음 단계 심사까지 남은 가설·증거
   - `git log --since --until --pretty=format:'%ad %s' --date=short`
   - WBS 진척: 일정 관리 도구가 GitHub이면 `python3 automation/scripts/wbs_sync.py pull` 후 `status`(완료율, 지난주 완료 WP, 지연·임박 WP). 다른 도구면 그 도구의 내보내기 CSV를 `M02_WBS.csv` 상태에 반영한 뒤 `status`
   - 프로토타입(V 트랙): 이번 주 테스트 세션 수, 가설별 중간 신호, timebox 남은 일수 (`03.docs/V.프로토타입/`)
   - `00.inbox/` 또는 `01.자료실/회사/`에 이슈 트래커(Jira·Linear) 내보내기 파일이 있으면 완료·신규·지연 이슈 집계 (집계는 스크립트로)
   - `02.wiki/domain/학사일정.md`와 회사 캘린더에서 다음 4주 안의 학사·영업 이벤트
3. **작성**: `04.ops/주간보고/_template.md` 구조로 `주간보고_D.md`를 만듭니다. 성과는 "무엇을 했다"보다 "무엇을 알게 됐고 무엇을 정했다" 중심으로 씁니다.
4. **리스크**: 게이트 미충족으로 막힌 산출물, `[확인 필요]`가 오래 남은 항목, 학사 일정과 충돌하는 계획을 리스크로 올립니다.
5. **공유용 변환**: 요청이 있으면 Slack·메일용 10줄 요약을 함께 만듭니다. 외부 공유본에는 회사 기밀 수치를 넣지 않습니다.
6. **log**: `## [YYYY-MM-DD] ops | 주간보고 D-6~D`

## 자동 실행

매주 금요일 실행은 `automation/README.md`의 "주간보고 예약" 절을 보세요. 예약 실행 결과는 초안이며 사람이 검토 후 공유합니다.
