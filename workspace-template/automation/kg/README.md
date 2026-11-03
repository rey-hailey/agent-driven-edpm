# 교육과정 지식그래프 (Curriculum KG)

2022 개정 국가 교육과정을 온톨로지로 정리한 공개 데이터 세 가지를 하나의 로컬 DB로 묶어, 기획·콘텐츠·AI·제안 작업에서 조회합니다.

| 원천 | 내용 | 라이선스 |
|------|------|----------|
| [korean-elementary-learning-map](https://github.com/DECK6/korean-elementary-learning-map) | 초등 11개 교과, 성취기준 620, 세부 토픽 1,956(평가 증거·평가 예시·오개념), 공식 선수 관계 416 + 권장 순서 1,877, 학습 묶음 152 | MIT |
| [korean-secondary-learning-map](https://github.com/DECK6/korean-secondary-learning-map) | 중학교 24과목(성취기준 714, 토픽 2,160), 고교 일반 231과목(성취기준 3,124), 직업계 528과목(선택), 공식·권장 선수 관계, 고교 과목 간 권장 순서, 이수학점·선택 묶음·예시 경로, 초→중(공식 290·후보 3,699)·중→고(175) 연결 | MIT (온톨로지 구조는 CC0 표기) |
| [transition-gap-map](https://github.com/DECK6/transition-gap-map) | 초→중 24과목·중→고 공통 37과목의 문서상 연계 격차 점수, 신규 성취기준 1,046(학부모용 쉬운 설명, AI 초안), 연계 근거 317, 학업성취도 평가 참고 수치 | MIT |

## 사용 순서

```bash
automation/kg/kg_sync.sh                  # 고정 커밋(sources.lock.json)으로 받기 → data/curriculum-kg/src/
python3 automation/kg/kg_build.py         # → data/curriculum-kg/kg.db (약 23MB, 1초 내외)
python3 automation/kg/kg_query.py stats   # 규모·버전·연결 점검
```

직업계 고교 과목까지 필요하면 `kg_build.py --with-vocational` (DB 약 120MB).

## 자주 쓰는 조회

| 질문 | 명령 |
|------|------|
| "일차방정식" 성취기준이 뭐가 있지? | `kg_query.py search 일차방정식 --level middle` |
| 이 성취기준의 선수·후속, 전환기 정보는? | `kg_query.py standard "[9수02-04]"` |
| 이차방정식까지 가려면 무엇을 먼저? | `kg_query.py path "[9수02-20]" --depth 4` (`--layer all`이면 권장 순서 포함, `--down`이면 후속) |
| 문항 만들 때 쓸 평가 증거·오개념은? | `kg_query.py seed "[6수02-04]"` |
| 우리 기능 설명에 맞는 성취기준 후보는? | `kg_query.py align 분수 덧셈 오답 해설 --level elementary` |
| 우리 콘텐츠가 교육과정을 얼마나 덮나? 빠진 선수 내용은? | `kg_query.py coverage 03.docs/3.설계/E11_교육과정매핑.csv --course 수학 --grade 7-9` |
| 중1·고1 전환기에 연계가 약한 과목은? | `kg_query.py gaps` / `kg_query.py gaps --subject 정보 --transition e2m` |
| 고교 공통 과목·과목 간 권장 순서는? | `kg_query.py courses --level high --category common` |
| 제안서용 성취기준 정합표 | `kg_query.py export --map 03.docs/3.설계/E11_교육과정매핑.csv --out 05.outputs/정합표_YYYYMMDD_HHMM.md` |

## DB 구조 (요약)

| 테이블 | 내용 |
|--------|------|
| standard | 성취기준 (level: elementary·middle·high·vocational, code, code_norm, 과목, 학년군, 영역, 요약, 근거 위치) |
| topic | 세부 토픽 (anchor·facet·auxiliary, 평가 증거·평가 예시·오개념 JSON) |
| alignment | 토픽 ↔ 성취기준 (assesses·supports·extends·introduces) |
| edge | 선수 관계: prereq_id → dependent_id, layer(official·candidate), edge_set(학교급 내·초→중·중→고), 근거 |
| course, domain, cluster, cluster_topic, course_relation, policy | 과목·영역·학습 묶음·고교 과목 순서·이수학점·선택 묶음·예시 경로 |
| gap_profile, gap_new_concept, gap_evidence, field_signal, subject_intro | 전환기 격차 |
| coverage_gap, release, meta, unresolved | 원천 데이터의 알려진 빈틈, 버전, 출처 고지, 연결 실패 |

직접 SQL로 볼 수도 있습니다: `sqlite3 data/curriculum-kg/kg.db "select code, summary from standard where course_label='수학' and grade_band='5-6'"`

## 반드시 지킬 것

1. **공식 자료가 아닙니다.** 교육부·국가교육위원회·NCIC의 승인이나 공식 해석이 아닙니다. 제출 문서에 성취기준 원문이 필요하면 근거 위치의 공식 고시 문서에서 확인합니다 (KG에는 원문이 아니라 요약이 있습니다).
2. **공식 관계와 권장 순서를 구분합니다.** `layer=candidate`는 저장소가 제안한 순서입니다. 화면·문서에서 "필수 선수"로 표현하지 않고 "권장 순서"로 씁니다.
3. **개별 학습자를 진단하지 않습니다.** 전환기 격차는 문서상 연계의 지표이지 학생 성취 수준이 아닙니다. 학부모 문구에 "뒤처짐·부족·미달·선행학습·불안" 같은 표현을 쓰지 않습니다.
4. **초안은 검토 후 씁니다.** 평가 증거·평가 예시·오개념(source-grounded-draft), 쉬운 설명(ai-draft)은 교사·교과 전문가 검토 후 학습자에게 내보냅니다.
5. **2022 개정만 다룹니다.** 2026년 기준 중3·고3은 2015 개정 교육과정을 적용받습니다 ([[domain/2022개정교육과정적용일정]]).
6. **버전을 고정하고 기록합니다.** 산출물에 KG 릴리스(`kg_query.py stats`)를 적습니다. 원천이 갱신되면 코드 의미가 바뀔 수 있습니다 (예: 초등 통합교과 `[2즐01-01]`~`[2즐03-04]`는 v0.5에서 같은 코드가 다른 성취기준을 뜻하게 됨).
7. **출처를 밝힙니다.** 산출물·제안서·제품 화면에서 KG 데이터를 쓰면 `kg_query.py`가 붙이는 출처 고지(MIT 저작권 표시 + 공식 근거 문서)를 남깁니다.

## 갱신

```bash
automation/kg/kg_sync.sh --check     # 새 커밋 확인
automation/kg/kg_sync.sh --update    # 최신으로 받고 lock 갱신
python3 automation/kg/kg_build.py    # 다시 빌드 → 연결 점검 확인
python3 automation/kg/kg_query.py coverage 03.docs/3.설계/E11_교육과정매핑.csv   # 매핑 영향 확인
```

원천 저장소의 CHANGELOG에서 코드·ID 변경을 확인하고, 바뀐 것이 있으면 `E11_교육과정매핑.csv`를 고친 뒤 lock과 함께 커밋합니다. 전환기 격차 데이터는 이전 버전 위에서 만들어졌으므로 빌드 결과의 "연결 점검"을 꼭 봅니다.
