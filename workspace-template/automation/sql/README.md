# automation/sql

지표·효과·대시보드 수치를 계산하는 SQL을 둡니다. 산출물(E07, E17, E19, F02, F04, N03, M04, M05, S03)에 적는 모든 수치는 여기 있는 쿼리나 `automation/scripts/metrics.py`로 계산하고, 산출물에 파일 경로를 적습니다. LLM이 수치를 추정하지 않습니다. 스킬: `/edpm-metrics`.

## 실행

```bash
python3 automation/scripts/metrics.py list                                   # 템플릿과 파라미터
python3 automation/scripts/metrics.py sample-db 05.outputs/sample.sqlite     # 기본 스키마 가상 데이터 (시험용)
python3 automation/scripts/metrics.py run 진도율 --db 05.outputs/sample.sqlite \
  --param from=2026-09-01 --param to=2026-09-30 --param course=C-MATH-1
python3 automation/scripts/metrics.py run 주간리텐션 --url "$DATABASE_URL" --param from=… --param to=… --param weeks=8
```

결과는 `05.outputs/metrics_<이름>_YYYYMMDD_HHMM.csv`. 보고서에 쓸 결과는 `01.자료실/데이터/YYYY-MM-DD_<지표>.csv`로 옮겨 보관합니다.

## 템플릿

| 파일 | 지표 | 쓰는 곳 |
|------|------|---------|
| `진도율.sql` | 학습자별 완료 단원 / 전체 단원, 80% 이상 학습자 수 | L03 PG, E07 참여, F02 기준선 |
| `수료율.sql` | 등록 코호트 중 수료 비율, 평균 소요일 | L03 CP, AT02 기업교육 보고 |
| `주간리텐션.sql` | 가입 주차 코호트별 n주 차 활성 비율 (리텐션 곡선) | N03 GT-01, AT07 소비자 앱 |
| `활성화.sql` | 가입 7일 내 핵심 행동 비율 | N03 GT-02, F02 |
| `과제제출률.sql` | 과제별 제출 학습자 / 등록 학습자 | E07 M-3x 교수자 도입, L04 |
| `정답률추이.sql` | 주차별 시도 정답률 | 학습 신호 (효과크기는 별도) |

효과크기: `metrics.py effect-size --csv <집단,값 CSV> --group group --value score`. 기준선·목표·실제 비교: `metrics.py compare`.

## 기본 스키마

템플릿은 아래 세 테이블을 가정합니다. 회사 DB가 다르면 **같은 이름의 뷰**를 만들거나 템플릿을 복사해 고치고, 매핑을 이 문서 끝에 적습니다. E12 학습데이터설계서의 이벤트(EV-ID)와 맞춥니다.

| 테이블 | 열 | 비고 |
|--------|----|------|
| `learners` | learner_key, segment, grade, joined_at | learner_key는 **가명 키** (E12 9절). 실명·연락처 없음 |
| `enrollments` | learner_key, course_id, enrolled_at, expires_at, completed_at, price | completed_at은 L03 수료 규칙 적용 결과 |
| `learning_events` | event_time, learner_key, event, course_id, unit_id, item_id, value, session_id | event 예: lesson_completed, attempt_submitted(value 1/0), assignment_submitted, hint_requested, live_session_presence |

## 규칙

| 규칙 | 내용 |
|------|------|
| 파일명 | `{지표ID}_{이름}.sql` 예: `M01_7일재풀이정답률.sql` (템플릿은 이름만) |
| 머리 주석 | 지표 정의(E07 링크), 대상 테이블(B03), 파라미터, 작성자, 검증 방법·결과 |
| 파라미터 | `{{from}}`, `{{to}}` 등 `{{이름}}` 형식, `--param 이름=값`으로 채움 |
| 검증 | 가상 데이터 10건으로 손계산과 일치하는지 확인하고 결과를 주석에 적음 |
| 개인정보 | 집계 수준으로만 내보냄. 학습자별 결과가 필요하면 가명 키만. 운영 DB에 쓰기 쿼리 금지 |
| 방언 | 템플릿은 SQLite 문법(`julianday`, `strftime`). PostgreSQL은 `extract(epoch …)/86400`, `to_char`로 바꿈 |

## 회사 스키마 매핑

| 기본 | 회사 테이블·열 | 비고 |
|------|----------------|------|
| {learning_events.event = lesson_completed} | {…} | {…} |
