---
name: edpm-curriculum
description: 2022 개정 국가 교육과정 지식그래프(초등·중등 학습지도, 전환기 격차 지도)를 받아 빌드하고 조회한다. 성취기준 검색·상세, 선수학습 경로, 문항·콘텐츠 씨앗(평가 증거·오개념), 우리 콘텐츠·기능의 성취기준 매핑과 커버리지, 빠진 선수 내용, 초→중·중→고 전환기 격차, 고교 과목 순서, 제안서용 정합표, 위키 교육과정 페이지 생성까지 한다. "성취기준 찾아줘", "교육과정 매핑", "커버리지", "선수학습", "전환기", "예비 중1", "정합표" 요청에 사용.
argument-hint: "<setup | search | standard | path | seed | map | coverage | gaps | courses | export | wiki | update> [인자]"
---

# edpm-curriculum

도구: `automation/kg/` (`kg_sync.sh`, `kg_build.py`, `kg_query.py`). 설명서: `automation/kg/README.md`.
매핑 파일: `03.docs/3.설계/E11_교육과정매핑.csv` (우리 콘텐츠·기능·진단 ↔ 성취기준).

## 지킬 것 (모든 하위 명령)

1. KG는 **공식 자료가 아니다.** 결과에 붙는 출처 고지를 지우지 않는다. 성취기준 원문이 필요한 제출 문서는 공식 고시 문서에서 확인하라고 안내한다.
2. **공식 관계(official)와 권장 순서(candidate)를 섞지 않는다.** 산출물·화면 문구에서 후보 관계를 "필수"로 쓰지 않는다.
3. **개별 학습자 진단 도구로 쓰지 않는다.** 전환기 격차는 문서상 연계 지표다. 학부모·학생 문구에서 "뒤처짐·부족·미달·선행학습·불안·격차" 표현을 피한다.
4. 평가 증거·평가 예시·오개념·쉬운 설명은 **초안**이다. 학습자에게 나가는 콘텐츠로 쓰려면 E11 검수 절차(교과 전문가)를 거친다.
5. **2022 개정만 다룬다.** 제품 대상 학년이 2015 개정을 적용받는 해라면 알린다 ([[domain/2022개정교육과정적용일정]]).
6. 산출물에 KG 릴리스(`kg_query.py stats` 첫 표)를 적는다.

## setup

1. `data/curriculum-kg/kg.db`가 없으면 `automation/kg/kg_sync.sh` → `python3 automation/kg/kg_build.py`를 실행한다. 직업계 고교가 대상이면 `--with-vocational`.
2. 빌드 출력의 "연결 점검"을 보고하고, 끊긴 참조가 있으면 어떤 조회에 영향이 있는지 설명한다.
3. `02.wiki/log.md`: `## [YYYY-MM-DD] curriculum | KG 빌드 — 릴리스 ...`

## search / standard / path / seed / courses

`kg_query.py`의 같은 이름 명령을 실행하고 결과를 요약해 보여준다. 결과가 길면 `--out 05.outputs/kg_<명령>_YYYYMMDD_HHMM.md`로 저장한다.
- `path`: 기본은 공식 관계만. 사용자가 학습 경로 설계(E08) 목적이면 `--layer all`로 권장 순서까지 보여주되 표시를 구분한다.
- `seed`: 문항 기획(E11)이나 AI 평가 세트(골든셋) 초안에 쓴다. 그대로 복사하지 말고 우리 제품 맥락으로 다시 쓰며, 출처 성취기준 코드를 남긴다.

## map — 성취기준 매핑

우리 콘텐츠·기능·진단 항목을 성취기준에 연결해 `E11_교육과정매핑.csv`에 쓴다.
1. 대상 목록을 모은다: E11 콘텐츠 유형(CT), E09 기능(F), E16 진단(DG), 문항 세트.
2. 항목마다 `kg_query.py align "<설명>" --level ... --course ... --grade ...`로 후보를 뽑는다.
3. 후보의 `standard`·`seed` 결과를 읽고 관계를 판단한다: `assesses`(직접 평가) / `supports`(학습 지원) / `extends`(심화) / `introduces`(도입). 판단 근거를 `근거` 열에 쓴다.
4. 표로 보여주고 **사람이 승인한 행만** CSV에 추가한다. `검토상태`는 처음에 `검토 전`.
5. 매핑 후 `coverage`를 바로 실행한다.

## coverage

`kg_query.py coverage 03.docs/3.설계/E11_교육과정매핑.csv --course <과목> --grade <학년군>`
- "지식그래프에 없는 코드"는 오타·표기 문제이므로 고친다.
- "빠진 공식 선수 성취기준"은 진단·복습 콘텐츠 후보로 E11·E16에 제안한다.
- "다루지 않은 성취기준"은 범위 결정 대상이다: 범위 밖이면 E06 범위 표에 명시, 다음 릴리즈면 E15에 반영.
- 결과를 `05.outputs/coverage_YYYYMMDD_HHMM.md`에 저장하고 E11 커버리지 절에 요약·경로를 적는다.

## gaps — 전환기

- 전체 순위: `kg_query.py gaps` (중학교에서 새로 시작하는 과목은 별도 표시).
- 과목 상세: `kg_query.py gaps --subject <과목> --transition e2m|m2h`.
- 활용처:
  - E04 시장·정책분석: 전환기 연계가 약한 과목 = 브리지 콘텐츠·진단 기회 (문서 지표임을 명시)
  - E16·E17: 예비 중1·고1 진입 진단은 `newlyIntroduced`와 연계 근거의 하위 학교급 토픽에서 문항 후보를 고른다
  - S05·`/edpm-doc content`: 예비 중1(초6 겨울방학)·예비 고1(중3 겨울방학) 시즌 콘텐츠, 쉬운 설명은 검토 후 사용
  - 학업성취도 평가 수치는 표집 기반 참고값이다. 효과 주장이나 원인 해석에 쓰지 않는다.

## export

제안서(S02)·기관 소개서·E05에 넣을 정합표: `kg_query.py export --map 03.docs/3.설계/E11_교육과정매핑.csv --out 05.outputs/정합표_YYYYMMDD_HHMM.md`. 출처 고지 문단을 문서에 함께 넣는다.

## wiki — 위키 교육과정 페이지

제품 범위(과목 × 학년군)에 해당하는 부분만 위키로 만든다. KG 전체를 위키에 복사하지 않는다.
1. `02.wiki/curriculum/<과목>-<학년군>.md` (type: curriculum-scope): 영역별 성취기준 표(코드·요약), 공식 선수 관계 요약, 전환기 정보, 우리 매핑 현황(커버리지 경로), KG 릴리스.
2. 제품의 핵심 성취기준(매핑에서 `assesses`인 것)은 `02.wiki/curriculum/standards/<코드>.md`로 만들 수 있다: `standard` + `seed` 요약, 현장 인사이트 링크(research/), 우리 콘텐츠 링크.
3. frontmatter `sources`에 `kg:<릴리스>`와 `kg_query.py` 명령을 적는다. `verified`는 빌드 날짜.
4. index·log를 갱신한다.

## update

`automation/kg/kg_sync.sh --check` → 새 커밋이 있으면 사용자에게 알리고, 승인하면 `--update` → `kg_build.py` → `coverage` 재실행 → 코드·ID 변경 영향(매핑 CSV, 위키 curriculum 페이지)을 보고한다. lock 변경은 사람이 확인 후 커밋한다.

## log

`## [YYYY-MM-DD] curriculum | {명령} {대상} — {요약}`
