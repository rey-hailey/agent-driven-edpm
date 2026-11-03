---
name: 작업 패키지 (WP)
about: WBS 작업. 보통 /edpm-wbs push가 M02_WBS.csv에서 만듭니다. 손으로 만들면 PM이 CSV에 반영합니다.
title: "[WP-x.x] "
labels: wp
assignees: ''
---

| 항목 | 값 |
|---|---|
| wp_id | WP-x.x |
| 단계 | 발견 / 정의 / 설계 / 구축 / 검증 / 출시 / 측정 / 관리 / 사업 |
| 산출물ID | 예: E09, V01 |
| 담당 | |
| 공수(일) | |
| 시작 | YYYY-MM-DD |
| 종료 | YYYY-MM-DD |
| 선행 | WP-x.x |
| 학사제약 | 예: 중간고사 동결 기간 피함 |

## 완료 기준

- [ ] 관련 산출물 `status`가 review 이상
- [ ]

> 진행 상태: 이슈를 닫으면 완료, 라벨 `상태:진행`·`상태:지연`으로 표시합니다. PM이 `/edpm-wbs pull`로 CSV에 가져옵니다.
