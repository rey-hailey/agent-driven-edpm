# 산출물 대시보드

산출물 진행 상태는 각 문서 frontmatter의 `status` 값만 기준으로 합니다. 이 페이지는 그 값을 모아 보여줄 뿐이며, 여기에 직접 상태를 적지 않습니다.

> **Dataview가 없을 때**: 이 페이지는 Obsidian 커뮤니티 플러그인 Dataview가 있어야 표로 보입니다. 플러그인이 없거나 Obsidian 밖(GitHub, 일반 편집기)에서 보면 아래 코드 블록이 그대로 보입니다. 이때는 Claude Code에서 `/edpm-lint`를 실행하면 산출물별 상태, 미완료 목록, 게이트 스킵 목록을 보고합니다. 터미널에서 빠르게 보려면 `grep -rH "^status:" 03.docs`도 쓸 수 있습니다.

## 1. 전체 산출물

```dataview
TABLE WITHOUT ID
  file.link AS "문서",
  doc_id AS "ID",
  title AS "산출물",
  stage AS "단계",
  module AS "모듈",
  status AS "상태",
  owner AS "담당",
  updated AS "갱신일"
FROM "03.docs"
WHERE doc_id
SORT doc_id ASC
```

## 2. 미완료 산출물

`done`과 `n/a`가 아닌 문서입니다. 전제조건(`requires`)을 함께 보고 다음에 쓸 문서를 고릅니다.

```dataview
TABLE WITHOUT ID
  file.link AS "문서",
  doc_id AS "ID",
  status AS "상태",
  requires AS "전제조건",
  module AS "모듈",
  updated AS "갱신일"
FROM "03.docs"
WHERE doc_id AND status != "done" AND status != "n/a"
SORT doc_id ASC
```

## 3. 검토 중

```dataview
LIST reviewers
FROM "03.docs"
WHERE doc_id AND status = "review"
SORT doc_id ASC
```

## 4. 해당 없음 (n/a)

모듈이 비활성이라 쓰지 않는 문서입니다. 사유는 각 문서 본문에 있어야 합니다.

```dataview
TABLE WITHOUT ID
  file.link AS "문서",
  doc_id AS "ID",
  module AS "모듈"
FROM "03.docs"
WHERE doc_id AND status = "n/a"
SORT doc_id ASC
```

## 5. 게이트 스킵 목록

`gate_skip`에 사유가 적힌 문서입니다. 스킵한 게이트는 출시 전에 해소해야 합니다.

```dataview
TABLE WITHOUT ID
  file.link AS "문서",
  doc_id AS "ID",
  status AS "상태",
  gate_skip AS "스킵 사유",
  updated AS "갱신일"
FROM "03.docs"
WHERE doc_id AND gate_skip
SORT doc_id ASC
```

## 6. 오래된 초안

30일 이상 갱신되지 않은 미완료 문서입니다. `updated` 값이 날짜 형식(YYYY-MM-DD)일 때만 정확합니다.

```dataview
TABLE WITHOUT ID
  file.link AS "문서",
  doc_id AS "ID",
  status AS "상태",
  updated AS "갱신일"
FROM "03.docs"
WHERE doc_id AND status != "done" AND status != "n/a" AND updated AND date(updated) < date(today) - dur(30 days)
SORT updated ASC
```

## 참고

- 상태 값: `draft | review | done | n/a`
- 게이트 규칙: 프레임워크 `guide/02.산출물체인과게이트.md`, 요약은 `AGENTS.md` 6장
- 완료 처리 시 `02.wiki/log.md`에 `## [YYYY-MM-DD] doc | Exx 산출물명 완료`를 추가합니다.

## 기능개선 과제 현황 (모드 F)

```dataview
TABLE initiative AS "과제", doc_id AS "문서", status AS "상태", updated AS "갱신"
FROM "03.docs/F.개선"
WHERE initiative AND !contains(file.path, "_과제템플릿")
SORT initiative ASC, doc_id ASC
```

## 신사업 단계 (모드 N)

```dataview
TABLE doc_id AS "문서", status AS "상태", updated AS "갱신"
FROM "03.docs/N.신사업"
WHERE doc_id
SORT doc_id ASC
```
