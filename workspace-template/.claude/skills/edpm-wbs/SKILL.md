---
name: edpm-wbs
description: 프로젝트 WBS와 일정(M02)을 만들고 일정 관리 도구와 동기화한다. 활성 산출물·기능·콘텐츠·프로토타입 작업을 작업 패키지로 나누고, 학사일정·변경 동결 기간을 반영해 일정을 잡고, 간트 차트를 만든다. 기본 도구는 GitHub(이슈·마일스톤·Projects)이며 스프레드시트·Notion·Jira·Linear로 내보낼 수 있다. 일정 변경 시 영향 분석도 한다. "WBS 만들어줘", "일정 계획", "간트", "GitHub 이슈로 올려줘", "진척 가져와", "일정 밀리면 어떻게 돼" 요청에 사용.
argument-hint: "[create | push | pull | status | update | impact <변경 내용> | export <jira|linear|notion|sheets> | setup]"
---

# edpm-wbs

원칙: **계획은 CSV, 진행은 도구.** `03.docs/M.관리/M02_WBS.csv`가 계획 필드(이름·단계·산출물·공수·날짜·선행·학사제약)의 정본이고, 일정 관리 도구가 진행 상태의 정본입니다. 도구 연동은 `automation/scripts/wbs_sync.py`로만 합니다 (생성·갱신이 반복 실행에도 중복되지 않음). 도구 설정은 `automation/wbs.json`과 `AGENTS.md` 2절 "일정 관리 도구". 상세: 프레임워크 `guide/12.일정관리도구연동.md`.

## create

1. **입력 확인**: M01 착수보고서(범위·마일스톤·기간), E00(활성 모듈), E09(기능 목록, 있으면), E11(콘텐츠 제작량, 있으면), E15(릴리즈 범위, 있으면), `02.wiki/domain/학사일정.md`, 회사 캘린더. M01이 `done`이 아니면 게이트 안내 후 멈춥니다.
2. **작업 분해**: 단계(발견·정의·설계·구축·검증·출시·측정) + 관리·사업 트랙으로 1단계를 나누고, 산출물 ID·기능 ID 단위로 2단계 작업 패키지(WP-1.1)를 만듭니다. 작업 하나는 5일 이하가 되게 쪼갭니다.
3. **에듀테크 제약 반영**
   - 교사 인터뷰·파일럿은 시험 기간과 방학을 피하고, 학기 초 2주는 학교 응답이 느리다는 점을 반영합니다 ([[domain/학사일정]]).
   - 학교·교육청 대상이면 개인정보·보안 심의, 학교운영위원회 심의 같은 외부 대기 기간을 별도 작업으로 넣습니다 [확인 필요: 고객별 절차].
   - 콘텐츠 제작은 집필 → 감수 → QA 순서와 감수자 가용 시간을 반영합니다. 국가 교육과정 기반이면 범위 성취기준 수(`kg_query.py coverage`)를 제작량 근거로 씁니다.
   - 게이트(G-SAFE, G-AI, G-EVIDENCE)를 마일스톤으로 둡니다.
4. **일정 계산**: 선행 관계와 공수로 시작·종료일을 계산합니다. 날짜 계산은 스크립트로 하고(주말·공휴일·변경 동결 제외), 주요 경로를 표시합니다.
5. **출력**
   - `03.docs/M.관리/M02_WBS일정계획.md` (계층표, Mermaid gantt, 주요 경로, 마일스톤·게이트 표, 버퍼)
   - `03.docs/M.관리/M02_WBS.csv` (헤더: `wp_id,이름,단계,산출물ID,담당,공수(일),시작,종료,선행,학사제약,상태,이슈`). 예시 행은 지웁니다.
   - 프로토타입(V 트랙)이 있으면 V01의 timebox를 WP로 넣습니다 (단계: 구축 또는 검증, 산출물ID: V01~V03).
6. **위험 연결**: 일정상 위험(촉박한 버퍼, 외부 대기)을 M03 위험대장 후보로 제안합니다.
7. **도구 반영 제안**: 일정 관리 도구가 정해져 있으면 `push`(GitHub) 또는 `export`(그 밖의 도구)를 제안합니다. 정해지지 않았으면 GitHub를 기본으로 권하고 저장소를 묻습니다.

## setup — GitHub 처음 연결

1. 확인: `gh auth status`(로그인), 저장소 존재. 저장소가 없으면 **비공개(private)** 로 만들지 묻습니다 — 워크스페이스에는 회사 기밀이 있으므로 공개 저장소에 올리지 않습니다. 개발팀 저장소에 이슈만 만들고 싶으면 그 저장소를 `repo`로 씁니다 (워크스페이스 파일은 올라가지 않음).
2. `automation/wbs.json`의 `repo`(owner/name), 필요하면 `project`(GitHub Projects 번호, `gh auth refresh -s project` 필요), `assignees`(담당 역할 → GitHub 아이디, 예: `{"개발 리드": "devlead"}`)를 채우고 `AGENTS.md` 2절 "일정 관리 도구"를 갱신합니다.
3. `python3 automation/scripts/wbs_sync.py setup --dry-run`으로 만들 라벨·마일스톤을 보여주고, 승인 후 `--dry-run` 없이 실행합니다.
4. Projects를 쓰면 날짜 필드 `시작`·`종료`(Date)를 만들고 Roadmap 보기를 `시작`~`종료`로 설정하도록 안내합니다 (필드 생성은 사람이 한 번).

## push — WBS → GitHub

1. `wbs_sync.py push --dry-run`으로 생성·갱신할 이슈 수와 명령을 보여주고 승인받습니다.
2. 승인 후 `push` 실행. WP마다 이슈(제목 `[WP-x.x] 이름`, 본문 = 계획 필드 표), 단계 마일스톤, 라벨을 만들거나 갱신하고, 이슈 번호를 CSV `이슈` 열에 기록합니다. CSV `상태`가 `완료`인 WP는 이슈를 닫습니다.
3. 닫힌 이슈를 CSV가 미완료로 가지고 있으면 기본은 GitHub 상태를 유지합니다(`pull` 권장). 다시 열려면 `--reopen`.

## pull — GitHub → CSV 상태

`wbs_sync.py pull`: 이슈 닫힘 → `완료`, 라벨 `상태:지연` → `지연`, `상태:진행` → `진행`. CSV에 없는 `wp` 이슈(팀이 직접 만든 작업)는 목록으로 보여주고 CSV에 추가할지 묻습니다. 추가하면 WP 번호를 붙이고 다음 `push`에서 제목이 맞춰집니다.

## status — 진척 요약

`wbs_sync.py status`: 상태별 개수, 완료율, 종료일 지난 미완료 WP, 7일 안에 끝나야 하는 WP. `/edpm-brief weekly`·`/edpm-brief report`가 이 결과를 씁니다. 도구를 쓰면 먼저 `pull`.

## update

1. 도구를 쓰면 먼저 `pull`로 진행 상태를 가져옵니다.
2. 산출물 frontmatter `status`와 맞춥니다: `done` 산출물의 WP인데 미완료면 완료로 바꿀지 묻습니다 (도구에서 닫는 것은 다음 `push`).
3. 지연된 WP와 영향받는 후속 WP를 보고하고, 계획을 바꾸면 CSV를 고친 뒤 `push`합니다.

## impact <변경 내용>

"교사 파일럿이 2주 밀리면?"처럼 변경을 받아 영향받는 WP, 밀리는 마일스톤, 학사일정과 새로 충돌하는 지점(예: 기말고사 기간으로 밀림), 대안 2~3개를 표로 보여줍니다. 결정되면 ADR로 남길지 묻습니다.

## export — 그 밖의 도구

`wbs_sync.py export --to <도구>`가 `05.outputs/wbs_<도구>_YYYYMMDD_HHMM.csv`를 만듭니다 (UTF-8 BOM, 엑셀에서 한글 유지).

| 도구 | 방법 | 상태 되돌리기 |
|------|------|---------------|
| 스프레드시트 (`sheets`) | Excel에서 열기, Google Sheets 가져오기. Google Sheets 연결 도구가 있으면 승인 후 시트에 직접 기록 | 시트의 `상태` 열을 CSV에 반영 |
| Notion (`notion`) | 페이지에서 Import → CSV로 데이터베이스 생성, `시작`·`종료`를 날짜 속성으로 바꾸고 Timeline 보기. Notion 연결 도구가 있으면 승인 후 직접 기록 | 데이터베이스를 CSV로 내보내 반영 |
| Jira (`jira`) | 외부 시스템 가져오기 → CSV, 날짜 형식 `yyyy-MM-dd`, `External ID` = wp_id | 필터 결과를 CSV로 내보내 반영 |
| Linear (`linear`) | 가져오기 → CSV, 상태는 Todo·In Progress·Done으로 변환됨 | CSV 내보내기 후 반영 |

외부 도구에 쓰는 작업(push, setup, 시트·Notion 직접 기록)은 실행 전에 대상과 건수를 보여주고 승인을 받습니다.

## log

`## [YYYY-MM-DD] doc | M02 WBS {생성|갱신} — WP N개, 주요 경로 N일`
