---
type: concept
status: draft
confidence: medium
sources: ["Baker (2001), The Basics of Item Response Theory", "NCES NAEP Technical Documentation", "Davey (2011), Practical Considerations in Computer-Based Testing", "Stocking & Lewis (1995), ETS RR-95-25"]
verified: 2026-10-14
updated: 2026-10-14
tags: [측정, IRT, CTT, CAT, 문항은행, 적응형검사, A08]
---

# 문항반응이론 (IRT)

> 문항 은행·적응형 문제·모의고사·배치고사를 설계할 때 참고. 아래 적용안은 공개 교육측정 원리를 제품 설계로 옮긴 실무 제안이다 [가정].

## 핵심 요약

- **IRT(Item Response Theory)**는 잠재 능력 θ에 따른 문항별 정답 확률을 모형화한다. 원점수 합계가 중심인 고전검사이론(CTT)과 관점이 다르다 (Baker, 2001, 1장).
- 이분 채점의 **1·2·3모수 로지스틱 모형**은 문항 난이도 b, 변별도 a, 하한 모수 c를 달리 사용한다. θ는 문항 모수가 아니라 응시자 능력이다 (Baker, 2001, 2장).
- **CAT(컴퓨터적응검사)**는 응답에 따라 능력을 다시 추정하고 다음 문항을 선택한다. 측정 효율만 아니라 내용 범위·문항 노출·종료 규칙을 함께 설계한다 (Davey, 2011).
- 문항 모수의 안정성은 무조건 보장되지 않는다. 모형 적합도·국소독립성·차원성과 시간에 따른 모수 변화를 확인해야 한다 (NCES, NAEP Technical Documentation).

## 상세

### 능력과 문항 모수

아래는 로지스틱 척도 상수를 1로 둔 표현이다. P는 정답 확률이고 exp는 지수함수다 (Baker, 2001, 2장).

| 모형 | 정답 확률 P(θ) | 문항별로 달라지는 모수 |
|------|----------------|------------------------|
| 1PL | 1 / (1 + exp(−(θ−b))) | b; a=1, c=0으로 고정한 표현 |
| 2PL | 1 / (1 + exp(−a(θ−b))) | a, b; c=0 |
| 3PL | c + (1−c) / (1 + exp(−a(θ−b))) | a, b, c |

- **b(난이도)**가 클수록 곡선이 높은 능력 쪽으로 이동한다. **a(변별도)**는 곡선의 가파름을 조절한다. 3PL의 **c**는 낮은 능력에서의 정답 확률 하한이며, 선다형 보기 수의 역수로 자동 확정하는 값이 아니다 (Baker, 2001, 1~2장).
- θ=b일 때 1PL·2PL의 정답 확률은 0.5, 3PL은 (1+c)/2다. 위 1PL 식은 Baker가 소개하는 Rasch 모형의 표현이다 (Baker, 2001, 2장).

### 고전검사이론(CTT) 대비

| 관점 | CTT | IRT |
|------|-----|-----|
| 분석의 중심 | 검사 점수와 문항의 관측 통계 | 능력에 조건부인 문항 반응 |
| 난이도 표현 | 응답 집단의 정답률 p | 능력 척도 위 문항 위치 b |
| 검사 구성 | 원점수와 문항 분석 활용 | 보정된 문항으로 목표 능력 구간의 정보 설계 |
| 비교할 때 조건 | 응답 집단·검사 구성을 함께 기술 | 같은 척도 연결과 모형 적합 확인 |

출처: Baker(2001), 1·3·6~8장. **p가 높으면 쉬운 문항, b가 높으면 어려운 문항**이므로 두 값을 같은 방향의 지표로 읽지 않는다 (같은 출처).

### 가정과 문항은행 보정

- 단일차원 모형은 주된 하나의 잠재 특성으로 반응을 설명한다 (Baker, 2001, 서론). 국소독립성은 능력을 조건으로 했을 때 문항 반응들이 독립이라는 가정이다. 한 문항의 답이 다음 답을 알려주는 구성은 별도 점검 대상이다 (NCES, NAEP Technical Documentation).
- **보정(calibration)**은 응답 자료에서 문항 모수를 추정하는 작업이다. 보정 집단·추정 방법·척도 기준을 기록하고, 새 검사·문항군은 공통 문항 등을 이용해 기준 척도로 연결한다 (Baker, 2001, 3·7장).
- 적합도가 나쁜 문항·국소의존·다차원성·모수 드리프트를 점검한다. IRT를 쓴다는 사실 자체가 이를 해결하지는 않는다 (NCES, NAEP Technical Documentation).
- 최소 응답 수를 일괄 지정하지 않는다 [확인 필요: 선택 모형·능력 분포·목표 추정 오차에 맞는 표본 계획]. 정답·지문을 수정한 문항은 새 버전으로 관리하고 재보정 여부를 검토한다 [가정: 문항은행 운영 제안].

### CAT 운영 흐름

| 단계 | 정할 내용 |
|------|-----------|
| 시작 | 초기 능력값·사전분포, 첫 문항 선택 |
| 반복 | 현재 능력에서 유용한 문항 선택 → 응답 → 능력·불확실성 갱신 |
| 제약 | 성취기준별 출제 비중, 동시 출제 금지 조합, 노출 관리 |
| 종료 | 정밀도 또는 분류 결정 기준과 최소·최대 문항 수 |
| 보고 | 능력 추정치·측정 오차, 배치 분류의 의미 |

출처: Davey(2011), *Practical Considerations in Computer-Based Testing*. 노출 제한은 측정 효율·검사 간 유사성·시험 보안과 함께 조정해야 한다 (Stocking & Lewis, 1995).

## 에듀테크 PM 적용

**체크리스트 (E11·E12·A08)** — 아래는 실무 설계 제안이다 [가정].

- [ ] 적응형 연습은 학습 지원, CAT는 측정이라는 목적 차이를 명세한다. 연습 중 힌트·재시도와 시험의 최초 응답을 구분해 저장한다
- [ ] 모의고사는 출제 범위와 기준 척도 연결 계획을 두고, 단순 정답률을 IRT 점수로 이름만 바꾸지 않는다
- [ ] 배치고사는 분류 경계·오배치 비용·경계 부근 재검사·교사 조정 경로를 정한다
- [ ] 문항은행에 문항 버전, 보정 자료, 모수·오차, 내용 태그, 적합도 점검, 노출 기록을 남긴다
- [ ] AI 생성 문항은 검토·시범 응답·보정 전까지 운영 문항과 분리한다 ([[domain/문항자동생성]])
- [ ] 능력 추정치가 올랐다는 것과 제품의 인과적 학습 효과를 구분해 평가한다 ([[domain/효과크기와증거수준]])

**관련 산출물**: E11, E12, E16, A08.

## 흔한 오해

- "IRT면 어느 집단에서도 같은 모수다" — 적절한 모형·척도·적용 맥락이라는 조건이 있다 (Baker, 2001, 3장; NCES NAEP).
- "CAT는 정답이면 한 단계 올리면 된다" — 능력 추정과 문항 선택 외에도 내용·노출 제약이 필요하다 (Davey, 2011).
- "θ가 학생의 고정된 지능이다" — 해당 검사가 측정하는 잠재 특성의 추정치다 (Baker, 2001, 1장).

## 관련 페이지

- [[domain/문항자동생성]] · [[domain/적응형학습]] · [[domain/효과크기와증거수준]]

## 출처

- Baker, F. B. (2001). *The Basics of Item Response Theory*, 2nd ed. ERIC Clearinghouse on Assessment and Evaluation. 서론·1~3·6~8장. https://eric.ed.gov/?id=ED458219 / 공개 전문: https://files.eric.ed.gov/fulltext/ED458219.pdf / 본문 확인에 사용한 대학 공개본: https://www.ime.unicamp.br/~cnaber/Baker_Book.pdf
- NCES. *NAEP Technical Documentation: Treatment of Items in NAEP to Avoid Violations of Assumptions*. https://nces.ed.gov/nationsreportcard/tdw/analysis/scaling_avoidviolat.aspx
- Davey, T. (2011). *Practical Considerations in Computer-Based Testing*. ETS. https://www.ets.org/Media/Research/pdf/CBT-2011.pdf
- Stocking, M. L., & Lewis, C. (1995). *A New Method of Controlling Item Exposure in Computerized Adaptive Testing*. ETS RR-95-25. https://www.ets.org/research/policy_research_reports/publications/report/1995/ihfd.html
