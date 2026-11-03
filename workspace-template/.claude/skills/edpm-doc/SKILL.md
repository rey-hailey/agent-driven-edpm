---
name: edpm-doc
description: 모든 산출물을 쓰고 갱신한다. 워크스페이스에 없는 산출물은 보관함(.edpm/library)에서 꺼내고, 게이트(전제조건·에듀테크 게이트)를 확인한 뒤 위키를 근거로 채운다. 트랙별 절차: 신사업 N01~N04(venture), 운영 개선 F00~F04·백로그(feature), 정책 P01~P09(policy), RFP·제안·견적 S01~S03(proposal), 세일즈·마케팅·안내문 S04·S05(content), 이해관계자 패널 비평(review). "E05 써줘", "학습성과설계서", "신사업", "기능 개선", "요청 들어왔어", "백로그", "환불 정책", "RFP", "제안서", "학부모 안내문", "리뷰해줘", "교사 입장에서", "어떤 문서가 더 있어" 요청에 사용.
argument-hint: "<ID> [--update] | list [검색어] | review <ID> | venture <opportunity | case | mvp | gate | plan> | feature <baseline | intake | prioritize | new | spec | launch | review | status> | policy <P0x | legal-check | sync | calc-refund> | proposal <analyze | gonogo | write | price | deck | check> | content <S04 | S05 | make | calendar | check>"
---

# edpm-doc

워크스페이스에는 **지금 경로의 산출물만** 있습니다. 설치 직후에는 E00 → PRD → E05 → E06 → E09 → 프로토타입(V)과 업무 모드 문서뿐이고, 나머지는 보관함 `.edpm/library/`에 있습니다. 필요해지면 이 스킬이 꺼내 씁니다. 무엇을 꺼낼지는 PRD가 정합니다 (미성년이면 E13, AI 기능이면 E14·A10·A14·A06, 유료 판매면 P01, 교과 연계면 E11, 연구 PoC면 D01, 효과를 주장하려면 E16·E17).

## 하위 명령

| 명령 | 읽을 파일 | 하는 일 |
|------|-----------|---------|
| `<ID>` | 이 파일 | 산출물 하나 작성·갱신 (없으면 보관함에서 꺼냄) |
| `list [검색어]` | 이 파일 | 보관함에 있고 아직 꺼내지 않은 산출물과 언제 쓰나 (`edpm_check.py library`) |
| `review` | `review.md` | 이해관계자 패널 비평 |
| `venture` | `venture.md` | 신사업 N01~N04 |
| `feature` | `feature.md` | 운영 개선 F00~F04, 요청 접수·백로그·우선순위 |
| `policy` | `policy.md` | 정책 P01~P09, 법령 확인, 환불 계산 |
| `proposal` | `proposal.md` | RFP 분석·Go/No-Go·제안서·견적·발표 자료 |
| `content` | `content.md` | 세일즈 플레이북·마케팅 계획·학부모 안내문·교사 가이드 등 |

하위 명령이면 같은 폴더의 해당 파일을 읽고 그 절차를 따릅니다. 그 파일 안에서 산출물을 쓸 때도 아래 공통 절차(꺼내기·게이트·근거)를 지킵니다.

## 절차

0. **PRD 먼저**: 루트 `PRD.md`를 먼저 읽습니다. 산출물의 내용은 PRD가 정한 제품 범위·목표·릴리스와 맞아야 하며, 범위를 바꿔야 하면 산출물이 아니라 PRD를 먼저 고칩니다(`/edpm-prd update`). PRD가 `review` 미만이면 G-PRD로 완료가 막힌다고 알리고 `/edpm-prd`를 제안합니다.
0.1 **회사 양식 확인**: `templates/회사양식/양식매핑.md`에 이 산출물이 매핑돼 있으면 따릅니다 — 방식 A면 회사 양식의 절 순서로 쓰고 회사 양식에 없는 EdPM 필수 항목은 끝에 "EdPM 필수 항목" 절로, 방식 B면 EdPM 템플릿으로 쓴 뒤 `/edpm-template apply <ID>`를 제안합니다. 매핑이 없으면 EdPM 템플릿으로 쓰고, 템플릿의 예시 행은 지웁니다. 어느 경우든 frontmatter는 유지합니다.
0.2 **E10(화면)이면**: 8절 화면별 구성을 2·3절의 모든 화면에 대해 한 번에 씁니다. 다 쓰면 화면 지도(대시보드의 화면 탭)에서 "구성 없음·상태 빠짐·끊긴 이동"이 0인지 보고, 보여줄 화면설계서가 필요하면 `python3 automation/scripts/edpm_screens.py --sb-md` → `sb-lowfi-pptx` 스킬(입력 `05.outputs/화면설계서.md`) → 필요하면 `sb-lowfi-figma`를 제안합니다.
1. **대상 확인·꺼내기**: 인자로 받은 산출물을 `03.docs/`에서 찾습니다. 없으면 `python3 automation/scripts/edpm_check.py add <ID>`로 보관함에서 꺼냅니다(딸린 CSV·템플릿 폴더도 함께). 무엇이 있는지 모르면 `list`(= `edpm_check.py library [검색어]`)로 보여주고 고르게 합니다. 꺼낸 문서의 전제가 워크스페이스에 없으면 "이번 경로에 없음"으로 보고 막지 않지만, 그 전제가 이 제품에 필요한지 한 줄로 묻습니다. 전용 스킬이 있는 산출물은 그 스킬의 절차를 함께 따릅니다: M01·M03~M05 `/edpm-brief report`, M02 `/edpm-wbs`, B06·B07 `/edpm-spec qa`, A00~A05·A07~A14 `/edpm-ai`, A06 `/edpm-ai eval`, P01~P09 `/edpm-doc policy`, N01~N04 `/edpm-doc venture`, F00~F04 `/edpm-doc feature`, V01~V03 `/edpm-proto`, E09(스펙) `/edpm-spec`, PRD `/edpm-prd`, S01~S03 `/edpm-doc proposal`, S04·S05 `/edpm-doc content`. 묶음(P1~P6)이면 각 산출물을 서브에이전트로 병렬 작성하고, 끝나면 ID 충돌과 상호 참조를 확인합니다.
   - 완료 처리(`status: done`) 저장은 PreToolUse 훅이 전제조건·게이트를 다시 확인합니다. 차단되면 사유를 사용자에게 전하고, 사용자가 명시적으로 허용할 때만 `gate_skip: [사유]`를 적어 다시 저장합니다 (우회하지 않음).

2. **게이트 체크** (`AGENTS.md` 6절, 상세는 프레임워크 `guide/02.산출물체인과게이트.md`)
   - `python3 automation/scripts/edpm_check.py start <문서 경로>`로 착수 가능 여부를 확인합니다(전제 산출물이 `done`·`n/a`, PRD가 `review` 이상). **A가 끝나야 B를 씁니다** — 훅이 전제 전 본문 쓰기를 막습니다. 사용자가 "미리 초안만"을 명시하면 `early_draft: [사유]`를 적고 씁니다.
   - 에듀테크 게이트를 확인합니다: E08·E09는 G-LEARN, E15는 G-SAFE·G-AI(A 트랙을 쓰면 A06 합격 포함)·G-CAL·G-CURRIC(국가 교육과정 기반이면), E18은 G-EVIDENCE·G-CAL·G-POLICY, M02는 G-CAL, F03은 G-IMPACT, V02(P3·P4)와 프로토타입 코드를 포함하는 E15는 G-PROTO, F02·F04는 G-MEASURE, 신사업의 E18은 G-STAGE. 산출물 "작성 가이드"의 적용 서비스 유형과 E00의 유형이 맞지 않으면 알립니다.
   - 미충족이면 부족한 항목과 먼저 할 일을 알리고 멈춥니다. `--force` 또는 "게이트 무시"가 명시되면 경고 후 진행하고 `gate_skip`에 사유를 적습니다.

3. **근거 수집**
   - `02.wiki/index.md`에서 관련 페이지를 찾아 읽습니다. 전제 산출물도 읽습니다.
   - 근거가 부족한 섹션이 있으면 작성 전에 알립니다: "E03을 쓰려면 `01.자료실/현장/` 원본이 3건 이상 필요한데 현재 1건입니다."
   - 사람이 그대로 진행하라고 하면 근거 없는 문장에 `[가정]`을 붙입니다.

4. **작성**
   - 템플릿 구조와 "작성 가이드"를 따르고, 템플릿의 예시 행(매스핏)은 실제 내용으로 바꾸거나 지웁니다.
   - 사실 주장 뒤에 `[[위키]]` 출처를 답니다. frontmatter `sources`에 근거 페이지를 적습니다.
   - ID 체계를 지키고, 전제 산출물의 ID를 추적 열에 연결합니다.
   - 수치 계산은 스크립트·SQL로 하고 경로를 적습니다.
   - 성취기준·선수 관계·전환기 정보는 `/edpm-curriculum`(KG 조회)으로 가져와 코드와 함께 씁니다. 템플릿의 "교육과정 지식그래프 연결" 절은 국가 교육과정 기반 제품일 때 채우고, 아니면 "해당없음"으로 둡니다.
   - `--update`면 바뀐 부분만 고치고, 끝에 `## 변경 이력`에 한 줄을 추가합니다.

5. **자체 점검**: 템플릿 끝의 "완료 체크리스트"를 채우고, 미충족 항목을 보고합니다. 실체 검증 항목(가이드 4.3)을 확인합니다.

6. **검토 제안**: 산출물별 추천 검토 패널로 `/edpm-doc review`를 제안합니다. (E05·E08: 교사+학습과학, E06: 교사+보호자+기관, E13: 보호자+법무 관점, E14·A03: 교사+학습자, S02: 기관 담당+교사, B01·B04: 개인정보·안전 검토자)

7. **상태 갱신**: 초안이면 `status: draft`, 검토 요청이면 `review`. 사람이 완료를 승인할 때만 `done`으로 바꾸고 `updated`를 기록합니다.

8. **log**: `## [YYYY-MM-DD] doc | E05 학습성과설계서 {초안|갱신|완료}`, 근거 페이지 수, `[가정]` 개수를 적습니다.

9. **위키 되돌리기**: 작성 중 정리된 결정은 `02.wiki/decisions/ADR-NNN`으로 남길지 묻습니다.

## 출력물 변환

- 화면 와이어프레임: E10 완료 후 `sb-lowfi-pptx` 또는 `sb-lowfi-figma` 스킬, 클릭 프로토타입은 `06.prototypes/_starter/click-prototype.html`
- Word·PDF 보고서: `python3 automation/scripts/edpm_export.py <md> --to html|pdf|docx` (표지·목차·쪽 번호, 회사 양식은 `--reference 회사양식.docx`). 공식 `docx`·`pdf` 스킬은 선택
- 파일명에 `_YYYYMMDD_HHMM`을 붙여 덮어쓰지 않습니다.
