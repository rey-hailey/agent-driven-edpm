---
type: standard
status: draft
confidence: medium
sources: ["https://adlnet.gov/past-projects/scorm", "https://userapps.support.sap.com/sap/support/knowledge/en/2506449", "https://sagroups.ieee.org/9274-3-1/how-to-participate", "https://adlnet.gov/news/2023/11/22/xAPI-Officially-Becomes-a-Published-IEEE-Standard", "https://rusticisoftware.com/blog/understanding-lti-13-vs-scorm-reeds-ltixcellent-adventure/"]
verified: 2026-10-12
updated: 2026-10-12
tags: [표준, SCORM, xAPI, cmi5, LTI, LRS, 이러닝패키징]
---

# SCORM과 xAPI (이러닝 패키징·추적 심화)

## 핵심 요약

- 표준 전체 지도는 [[domain/상호운용표준]]에 있다. 이 페이지는 **이러닝 콘텐츠를 LMS에 넣고 기록을 받는 방식**만 깊게 다룬다.
- 네 가지는 해결하는 문제가 다르다: **SCORM** = 콘텐츠 패키지 + LMS 안 실행·추적, **xAPI** = 어디서든 학습 경험 기록(LRS 저장), **cmi5** = xAPI로 "LMS가 콘텐츠를 실행"하는 규칙, **LTI 1.3** = LMS가 외부 호스팅 도구를 안전하게 실행(패키지를 옮기지 않음).
- SCORM 2004 4th Edition(2009)이 ADL이 안내하는 최신 SCORM 판이다 (https://adlnet.gov/past-projects/scorm) [verified 2026-10-12, 검색 결과 요약 기준]. 현장에서는 SCORM 1.2도 여전히 널리 쓰인다 [가정].
- xAPI 2.0은 IEEE 9274.1.1-2023으로 발행되었다 (ADL, https://adlnet.gov/news/2023/11/22/xAPI-Officially-Becomes-a-Published-IEEE-Standard). cmi5의 IEEE 표준화(P9274.3.1)는 IEEE에 "P"(진행 중 프로젝트)로 등재되어 있다 (https://sagroups.ieee.org/9274-3-1/how-to-participate) [verified 2026-10-12: 진행 중으로 확인, 발행 여부는 계속 확인 필요].

## 상세

### SCORM 1.2 vs 2004

| 항목 | SCORM 1.2 | SCORM 2004 (3rd·4th Ed.) |
|------|-----------|---------------------------|
| 실행 방식 | 콘텐츠가 LMS 창 안의 JavaScript API와 통신 | 같음 (API 이름·데이터 모델 다름) |
| 상태 값 | `lesson_status` 하나(passed·completed 등 혼합) | 완료(`completion_status`)와 합격(`success_status`) 분리 |
| `suspend_data` (이어 보기 상태 저장) | 4,096자 (SAP KB, https://userapps.support.sap.com/sap/support/knowledge/en/2506449) | 64,000자 (3rd·4th Ed., 같은 출처) |
| 순서·분기(sequencing) | 없음 | Simple Sequencing 기반 규칙 정의 가능 |
| 실무 평판 | 단순, LMS 호환성 높음 [가정] | 기능 많으나 LMS별 구현 편차 [가정] |

- `suspend_data` 한도 초과는 "이어 보기가 안 된다"는 흔한 장애 원인이다. 저작 도구 압축 옵션, 2004 전환, 북마크만 저장하기로 대응한다 (SAP KB 위 링크).
- SCORM은 브라우저 안 LMS 세션이 전제라 모바일 앱·오프라인·LMS 밖 활동 추적에 약하다.

### xAPI와 LRS

- 기록 단위는 **statement**: 행위자(actor) – 동사(verb) – 대상(object) + 결과(result)·맥락(context). 예: "학습자 A가 시뮬레이션 B를 완료함, 점수 0.8".
- 저장소는 **LRS(Learning Record Store)**. LMS와 분리될 수 있고, 여러 시스템의 기록을 모은다.
- **동사·활동 ID를 통제하지 않으면** 데이터가 섞여 분석할 수 없다. 프로필(profile)과 동사 목록을 먼저 정한다 [가정].
- xAPI는 "기록 형식"이다. 실행·완료 판정 규칙은 정하지 않는다.

### cmi5

- xAPI 위에 LMS 실행(launch), 세션, 완료·합격 판정 규칙(moveOn)을 정의한 프로필. SCORM의 "LMS가 콘텐츠를 실행하고 결과를 받는" 모델을 xAPI로 옮긴 것이다.
- AICC에서 시작해 2014년 ADL로 이관, 첫 정식판(Quartz)이 나왔다 (Learning Guild 보도, https://learningguild.com/articles/1977/adl-cmi5-committee-announces-release-of-quartz-version-of-cmi5-specification) [발표일 확인 필요].
- 콘텐츠를 LMS 밖(CDN 등)에 둘 수 있어 모바일·대용량 콘텐츠에 유리하다.

### LTI 1.3과의 차이

| 질문 | SCORM·cmi5 | LTI 1.3 |
|------|------------|---------|
| 콘텐츠는 어디에? | 패키지를 LMS(또는 cmi5는 외부)에 업로드 | 도구 제공자 서버에 그대로 |
| 업데이트 | 패키지 재배포 | 제공자가 고치면 즉시 반영 |
| 성적 반환 | 데이터 모델에 포함 | LTI Advantage AGS 서비스 필요 (https://rusticisoftware.com/blog/understanding-lti-13-vs-scorm-reeds-ltixcellent-adventure/) |
| 콘텐츠 선택 | 패키지 단위 등록 | Deep Linking으로 LMS 안에서 항목 선택 |
| 유출 위험 | 패키지가 고객 LMS에 복사됨 | 콘텐츠가 제공자 서버에 남음 |

### 언제 무엇을 쓰나 (판단 기준)

1. 고객 LMS가 무엇을 지원하나? → 기업 고객은 SCORM 1.2를 최소 공통분모로 요구하는 경우가 많다 [가정].
2. 콘텐츠를 계속 고치고 고객 LMS에 복사되면 안 되나? → LTI 1.3 또는 "SCORM 래퍼(dispatch) 패키지"(실제 콘텐츠는 원격 호스팅) [가정].
3. LMS 밖 활동(현장 실습, 앱, 시뮬레이션) 기록이 필요하나? → xAPI + LRS.
4. 패키지 실행 + 풍부한 기록이 모두 필요하나? → cmi5 (LMS 지원 여부 확인).

### 전환 팁

- SCORM → cmi5: 완료·합격 규칙을 moveOn으로 매핑, `suspend_data` 대신 State API 사용.
- 이벤트 로그(E12)를 처음부터 xAPI statement로 변환 가능하게 설계하면 나중 비용이 줄어든다 ([[domain/상호운용표준]]).
- 시험 도구: SCORM Cloud(Rustici) 같은 테스트 LMS로 패키지 실행·데이터 기록을 검증한다 [가정: 제품 기능은 공식 페이지 확인]. ADL은 xAPI·cmi5 적합성 테스트 도구를 공개해 왔다 [확인 필요].

## 서비스 유형별 차이

| 유형 | 필요 수준 |
|------|-----------|
| AT01 이러닝 마켓플레이스 | 자체 플레이어 중심, B2B 판매 시 SCORM 내보내기 요구 [가정] |
| AT02 기업교육 LMS | SCORM 1.2/2004 수입 필수, xAPI·cmi5 선택, HRIS 연동 |
| AT03 부트캠프 | 표준보다 자체 LMS·코드 실습 환경 연동 |
| AT05 K-12 | LTI·OneRoster가 더 중요(해외), 국내는 교육청 시스템 연동 [확인 필요] |
| AT08 고등·평생교육 | LTI 1.3 도구 연동이 중심 |

## 에듀테크 PM 적용

- [ ] 고객 LMS의 지원 표준·버전을 영업 단계에서 수집했다 (S01, L05)
- [ ] 패키지 방식과 원격 실행(LTI·래퍼) 중 콘텐츠 보호 요구에 맞게 골랐다 (L05, P03)
- [ ] `suspend_data` 한도 등 버전별 제약을 테스트 시나리오에 넣었다 (B06)
- [ ] xAPI 동사·활동 ID 목록을 E12에 정했다
- [ ] 진도·완료 규칙(L03)이 SCORM 상태 값 또는 cmi5 moveOn에 어떻게 매핑되는지 표로 정리했다
- [ ] 테스트 LMS에서 실행·재개·완료·점수 반환을 검증했다 (B07)

## 흔한 오해

- "xAPI가 SCORM을 대체했다" — xAPI는 기록 형식이다. LMS 실행 대체는 cmi5다.
- "SCORM 2004가 항상 낫다" — 고객 LMS가 1.2만 안정적으로 지원하면 1.2가 맞다.
- "LTI 지원 = 성적 반환" — 기본 실행만 지원하는 경우가 있다. AGS 지원 여부를 따로 확인한다.

## 관련 페이지

[[domain/상호운용표준]] · [[domain/학습진도관리]] · [[domain/학습콘텐츠구조]] · [[domain/학습분석지표]] · [[domain/수료증과디지털크레덴셜]]

## 출처

- ADL, SCORM(과거 프로젝트): https://adlnet.gov/past-projects/scorm
- ADL, xAPI IEEE 표준 발표: https://adlnet.gov/news/2023/11/22/xAPI-Officially-Becomes-a-Published-IEEE-Standard
- IEEE SA, P9274.3.1 xAPI cmi5 Working Group: https://sagroups.ieee.org/9274-3-1/how-to-participate
- SAP Knowledge Base 2506449 (suspend_data 한도): https://userapps.support.sap.com/sap/support/knowledge/en/2506449
- Rustici Software, LTI 1.3 vs SCORM: https://rusticisoftware.com/blog/understanding-lti-13-vs-scorm-reeds-ltixcellent-adventure/
- Learning Guild, cmi5 Quartz 발표: https://learningguild.com/articles/1977/adl-cmi5-committee-announces-release-of-quartz-version-of-cmi5-specification
