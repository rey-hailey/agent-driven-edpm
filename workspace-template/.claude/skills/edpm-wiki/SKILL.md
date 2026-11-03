---
name: edpm-wiki
description: 근거 자료와 지식을 관리한다. ingest: 00.inbox·파일·URL을 비식별화해 01.자료실에 넣고 위키를 갱신. query: 위키 근거로 답. lint: 위키·산출물 점검(모순·오래된 정보·끊긴 링크·출처 없는 주장·개인정보·게이트 스킵). library: 자료실 목록·검색·공유 번들·NotebookLM 동기화. collect: Aside 레시피로 웹 수집. promote: 일반 지식을 기밀 제거 후 개인 Brain으로. "자료 넣어줘", "인박스 처리", "이 인터뷰 정리해서 위키에", "위키에서 찾아줘", "우리가 아는 게 뭐야", "점검", "헬스체크", "자료 찾아줘", "수집해줘", "리뷰 모아줘", "브레인으로 승격" 요청에 사용.
argument-hint: "ingest [파일|URL] | query <질문> | lint [wiki|docs|pii|all] | library <catalog|find|stale|bundle|nlm-sync> | collect <R01~R08> | promote [--dry-run]"
---

# edpm-wiki

사람은 자료를 고르고 질문하고 판단합니다. 요약·교차 참조·정리는 에이전트가 합니다 (AGENTS.md 4절 위키 규칙, 7절 데이터 보호).

## 하위 명령

| 명령 | 읽을 파일 | 하는 일 |
|------|-----------|---------|
| `ingest` | `ingest.md` | 자료 → 개인정보 확인·가명화 → 자료실 → 위키 갱신 → index·log |
| `query` | `query.md` | 위키 근거로 답, 재사용할 답은 05.outputs와 위키로 |
| `lint` | `lint.md` | 위키·산출물 점검 (결정적 항목은 `edpm_check.py report`) |
| `library` | `library.md` | 자료실 목록·검색·오래된 자료·공유 번들·NotebookLM |
| `collect` | `collect.md` | Aside 웹 수집 레시피 |
| `promote` | `promote.md` | 일반 지식 → 개인 Brain (기밀 제거, 사람 승인) |

명령 없이 부르면 `00.inbox/`에 처리할 자료가 있는지 보고 `ingest`를 제안하고, 없으면 `lint` 요약을 보여줍니다. 해당 파일을 읽고 그 절차를 따릅니다.
