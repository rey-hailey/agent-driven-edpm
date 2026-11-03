---
name: edpm-metrics
description: 지표를 정의하고 SQL·스크립트로 계산한다. E07 지표(M-ID)를 이벤트(E12)에 연결해 SQL을 만들고, automation/sql 템플릿(진도율·수료율·주간 리텐션·활성화·과제 제출률·정답률 추이)을 회사 DB에 맞춰 실행하며, 효과크기(Cohen's d)와 기준선·목표·실제 비교표를 만든다. 산출물(E07·E17·E19·F02·F04·N03·M04)에 적는 모든 수치의 계산 경로를 남긴다. "지표 계산해줘", "진도율 뽑아줘", "리텐션 곡선", "효과크기", "기준선 잡아줘", "SQL 만들어줘", "수치 확인" 요청에 사용.
argument-hint: "<define <M-ID> | sql <M-ID|이름> | run <이름> [--db|--url] [--param k=v] | effect <csv> | compare <M-ID> | baseline <F02|N03> | connect>"
---

# edpm-metrics

원칙 (AGENTS.md 8절, G-MEASURE): **수치는 스크립트가 계산하고 LLM은 해석만 합니다.** 결과 CSV 경로와 SQL 파일명을 산출물에 적습니다. 학습자별 결과는 가명 키만 쓰고 집계 수준으로 내보냅니다.

도구: `automation/scripts/metrics.py` (sqlite 내장, PostgreSQL은 `psql`), 템플릿 `automation/sql/*.sql`, 기본 스키마 `automation/sql/README.md`.

## connect — 데이터 연결 (처음 한 번)

1. 회사 분석 DB가 무엇인지 묻습니다: PostgreSQL·MySQL·BigQuery·Redshift / 추출 CSV / 아직 없음.
2. **PostgreSQL**: `DATABASE_URL`을 환경변수로만 받습니다(파일에 쓰지 않음, `.env`는 git 제외). `metrics.py run ... --url "$DATABASE_URL"`.
3. **그 밖의 DB·CSV**: 추출 CSV를 `01.자료실/데이터/`에 넣고(가명 키만), sqlite로 적재하는 방법을 안내합니다 (`sqlite3 db.sqlite ".import --csv 파일 테이블"`). BigQuery 등은 회사 도구에서 집계 CSV를 받습니다.
4. **아직 없음**: `metrics.py sample-db`로 기본 스키마 가상 데이터를 만들어 지표 정의와 SQL을 먼저 검증하고, E12에 필요한 이벤트를 적습니다.
5. 회사 스키마가 기본 스키마와 다르면 같은 이름의 뷰(`learning_events`, `enrollments`, `learners`)를 만들거나 SQL 템플릿을 복사해 고칩니다. 매핑을 `automation/sql/README.md` 아래에 기록합니다.
6. 학생 개인정보가 보이는 테이블에는 직접 쿼리하지 않습니다 (AGENTS.md 7절). 집계 뷰나 가명 키 테이블만.

## define <M-ID>

E07 지표 정의표의 행을 완성합니다: 이름, 정의(계산식), 분자·분모, 필요한 이벤트(EV-ID, 없으면 E12에 추가 제안), 집계 주기, 세그먼트(학년·기관·플랜), 가드레일 여부, 반(反)지표. 학습 효과 지표는 측정 설계(E16)와 연결합니다. 정의가 모호하면 두 사람이 다른 수치를 낼 수 있는 지점을 지적합니다.

## sql <M-ID|이름>

1. 가장 가까운 템플릿을 고릅니다 (`metrics.py list`). 없으면 기본 스키마로 새로 씁니다.
2. 머리 주석에 지표 정의(E07 링크), 대상 테이블, 파라미터, 검증 방법을 적습니다. 파일명 `automation/sql/{M-ID}_{이름}.sql`.
3. **검증**: `sample-db` 또는 가상 10행으로 손계산과 비교한 결과를 주석에 남깁니다.
4. E12 3절 "이벤트 → 지표 매핑"에 SQL 경로를 적습니다.

## run <이름>

`metrics.py run <이름> --db <sqlite> | --url "$DATABASE_URL" --param from=… --param to=… …`를 실행하고, 결과 표와 저장 경로(`05.outputs/metrics_*.csv`)를 보여줍니다. 운영 DB에 쓰는 쿼리(insert·update·delete)는 만들지 않습니다. 실행 전에 대상 DB와 기간을 확인받습니다.

## effect <csv>

`metrics.py effect-size --csv … --group … --value …`로 Cohen's d와 95% 신뢰구간을 계산하고, 증거 수준을 [[domain/효과크기와증거수준]] 기준으로 적습니다. 신뢰구간이 0을 포함하거나 표본이 30 미만이면 그렇게 적고, 제안서·마케팅에서 과장하지 않도록 경고합니다 (설계 원칙 7). 비교집단이 없으면 "전후 비교"임을 명시합니다.

## compare <M-ID>

F02·N03의 기준선·목표와 지금 계산한 실제값을 `metrics.py compare`로 표로 만들어 F04·N04 판정에 붙입니다. 같은 SQL, 같은 기간 정의인지 확인합니다 (G-MEASURE).

## baseline <F02|N03>

과제·신사업의 목표 지표마다 지금 기준선을 계산해 문서의 기준선 칸을 채웁니다 (기간, SQL 경로 포함). 데이터가 없으면 `[가정]`으로 두고 무엇을 계측해야 하는지 E12에 제안합니다.

## log

`## [YYYY-MM-DD] metrics | {M-ID 또는 이름} {run|effect|baseline} — {결과 경로}`
