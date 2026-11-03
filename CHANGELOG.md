# CHANGELOG

Agent Driven EdPM 변경 이력입니다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/), 버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

- MAJOR: 폴더 체계·층 구조·흐름 게이트 변경
- MINOR: 산출물·게이트·스킬·스크립트 추가·삭제
- PATCH: 템플릿 문구, 오타, 설명 보완

## [Unreleased]

### Added — AI 프로덕트 기획 실무 대응 (텍스트 스펙·상태 흐름·연구 이관·포트폴리오)
- **E09 유저스토리·상태 흐름**: 기능마다 유저스토리(US, 스토리마다 확인하는 AC) → 인수조건 → 상태 흐름(Mermaid `stateDiagram-v2`: 빈 상태·실패·시간 초과·권한 없음·오프라인·사람 이관) 순서. `/edpm-spec check`가 `F → US → AC → T` 추적과 상태 흐름 누락을 점검
- **E14 2.1 AI 응답 흐름**: 입력 검사 → 근거 조회 → 생성 → 출력 검사 → 표시, 거절·대체·교사 이관 분기마다 기준(GR·시간·비용 한도)·화면 문구·로그·평가 시나리오, 응답 시간·비용·정확도 트레이드오프 기록. E14 체크리스트의 옛 분류 표현("유형 A/B/C")을 구성 요소로 수정
- **D 연구 이관 트랙**: `03.docs/D.연구이관/D01_연구PoC제품화검토서.md` — 연구·교과 조직의 PoC·학습 알고리즘을 제품 기능·프로세스·데이터 구조로 옮김(결론, 연구 측 사실, 재현 가능한 알고리즘 명세, 제품 관점 전환표, 데이터·동의, 제품화 조건, 남은 불확실성 HY-D, 연구 조직과의 합의, PRD·E06·E12 반영). 산출물 템플릿 총 84종(PRD 포함), 모듈 RND. `edpm-prd`·E06이 D01을 입력으로
- 스킬 `edpm-portfolio` — 총 33종: 한 사이클을 포트폴리오 한 장으로(문제 정의 → 결정과 이유·적중 → 개발이 참조한 산출물 → AI 결과 검증 방법 → 결과 지표 → 배운 것), `check`로 개인정보·기밀·식별 정보·수치 출처 점검 후 `edpm_export.py`로 HTML
- `edpm_check.py portfolio [--ids …] [--adr …]`: 포트폴리오용 사실(JSON) — 기간, 문서 상태, 스펙 규모(기능·유저스토리·인수조건·상태 흐름·작업), 미해결 `[가정]`·`[확인 필요]`, 게이트 기록, 결정 목록과 적중률, 프로토타입. 템플릿 예시 행은 세지 않음. 진행표 트랙 순서에 D
- 회귀 테스트 2건(포트폴리오 사실·예시 제외·적중률, D01 생성 게이트) — 총 24건

## [1.0.0] - 2026-11-03

첫 공개 버전. 에듀테크 PM이 PRD에서 출발해 상세 요구사항 → 스펙 → 프로토타입·구현 → 출시까지 Claude Code와 함께 진행하는 프레임워크.

### 흐름과 하네스
- **PRD 원점**: 워크스페이스 루트 `PRD.md`(만들 제품 전체, 릴리스 계획, 프로토타입으로 보여줄 정수, 개발 체계). 상세 요구사항(E06) → 기능명세 = 스펙(E09: 인수조건·입출력 계약·작업·테스트 추적)
- **A가 끝나야 B**: 생성 게이트(전제조건이 끝나기 전 산출물 본문 쓰기 차단), 완료 게이트(전제·흐름·에듀테크 게이트), G-PRD·G-SPEC, 진행표(`edpm_check.py progress`), 지금 단계(`phase`), 세션 시작 상황판
- 개발 체계 구분: 개발팀(PM은 스펙까지, `/edpm-handoff dev`) / 바이브코딩(스펙 승인 후 `src/`에 구현, `/edpm-spec build`)
- PreToolUse 훅: 자료실 원본 보호, 식별 정보 저장 차단, 제품 코드 게이트

### 에듀테크 특화
- 산출물 템플릿 83종: 제품(E00~E20), 관리(M), 구현(B), AI(A00~A14), 사업(S), 학습운영(L), 정책·운영(P), 신사업(N), 운영 개선(F), 프로토타입(V)
- 게이트: G-LEARN·G-SAFE·G-AI·G-EVIDENCE·G-CAL·G-POLICY·G-STAGE·G-IMPACT·G-MEASURE·G-PII·G-PROTO·G-CURRIC
- 업무 모드(신사업 N / 운영 개선 F), 서비스 유형 15종(AT01~AT15)
- AI 기능 분류: 교육적 역할(T·F·G·P·O) × 구성 요소(근거·학습자상태·데이터조회·생성물·대화), AI 방식 스펙트럼(A10), 평가(`ai_eval.py`), 비용(`ai_cost.py`)
- 2022 개정 교육과정 지식그래프 연동(`/edpm-curriculum`), 개인 EdTech Brain 지식 92쪽

### 도구
- 스킬 32종(`/edpm-start`, `/edpm-init`, `/edpm-prd`, `/edpm-spec`, `/edpm-doc`, `/edpm-proto`, `/edpm-template`, `/edpm-handoff` 외)
- 스크립트: 점검기·훅, 지표 계산(`metrics.py` + SQL 템플릿), WBS ↔ GitHub 동기화(`wbs_sync.py`), 산출물 내보내기(`edpm_export.py`: HTML·PDF·Word)
- 대화형 설치(`./install.sh`), 사전 점검(`--check`), 업그레이드(`--upgrade`), 선택 설치(`--extras`: sb-lowfi)
- 회사 문서 양식 연결(`templates/회사양식/`, 방식 A 회사 양식 구조로 작성 / B 회사 양식으로 옮기기)
- 가이드 00~15, 마스터 가이드 HTML, 회귀 테스트 22건
