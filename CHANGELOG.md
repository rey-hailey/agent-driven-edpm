# CHANGELOG

Agent Driven EdPM 변경 이력입니다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/), 버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

- MAJOR: 폴더 체계·층 구조·흐름 게이트 변경
- MINOR: 산출물·게이트·스킬·스크립트 추가·삭제
- PATCH: 템플릿 문구, 오타, 설명 보완

## [Unreleased]

### Changed — 리서치가 먼저, 기능 고도화도 스펙으로 넘김
- **리서치는 PRD보다 먼저**: PRD의 입력인 E01~E04(발견)·N01(사업기회)·F00(현황 진단)·D01(연구 이관)은 G-PRD 예외 — PRD 전에 착수·완료 가능. 단계 "1 PRD"가 N01·F00·위키 수집을 먼저 안내하고, `/edpm-prd`가 그 결과를 1·2절에 담음
- **F02 기능기획서 = 기능 단위 스펙**: 2.1 상태 흐름, 5.1 입출력 계약과 작업 분해(T)·테스트 추가. 개발팀이 프로토타입이 아니라 F02를 기준으로 구현. `/edpm-spec check·tasks·build`가 F02 경로를 받음, 화면 구조가 바뀌면 E10(IA) 갱신
- `/edpm-prd path`에 보고 체계(착수·중간·완료 보고 → M01·M02·M03)와 개발 연동(B01) 행 추가
- README·AGENTS 흐름도에 리서치 → PRD, 보고·위키가 함께 도는 것을 표시

### Added — 작업 환경: Antigravity + Claude Code 확장
- 권장 작업 환경을 **Antigravity(에디터) + Claude Code 확장(에이전트)** 으로: 산출물을 탐색기에서 바로 열고 마크다운·Mermaid 미리보기로 확인하면서 작업. 스킬·훅은 Claude Code 기능이므로 에디터 내장 에이전트가 아니라 Claude Code 패널에서 작업하도록 안내
- 워크스페이스 `.vscode/` 기본 포함(Antigravity·Cursor·VS Code 공통): 권장 확장(Claude Code, Markdown Mermaid, Rainbow CSV), 마크다운 줄바꿈, 검색에서 보관함·지식그래프 제외. `--upgrade`가 없으면 추가
- `install.sh`: 끝 안내를 "Antigravity에서 폴더 열기 → Claude Code 패널에서 /edpm-start"로, 대화형 설치 끝에 Antigravity로 바로 열지 물음(macOS), `--check`가 Antigravity·VS Code 계열 에디터 확인
- guide 00 2절 "작업 환경" 신설(설정 순서, 일하는 모습, 다른 환경), README·CLAUDE.md·guide 14 시작 안내 반영. 워크스페이스 `.gitignore`의 강의 자료 유래 항목 제거
- 회귀 테스트: 설치 시 `.vscode` 권장 확장·검색 제외 확인

### Changed — 단순화: 핵심 경로 + 보관함, 스킬 15종, 기준 문서 한 곳
목표는 한 사이클(PRD → 스펙·프로토타입 → 결정 → 출시 → 효과 리뷰)을 더 빨리 돌리는 것. 같은 기능을 덜 보이게 하고, 같은 내용을 한 곳에만 둔다.
- **워크스페이스는 핵심 경로만**: 설치 시 E00·PRD·E05·E06·E09·V(프로토타입)·WBS CSV + 업무 모드 문서(N01·N03·N04 또는 F00·백로그·과제 템플릿)만 `03.docs/`에. 나머지 산출물은 프레임워크 `library/` → 워크스페이스 `.edpm/library/` 보관함. `edpm_check.py library [검색어]`(꺼내지 않은 산출물·언제 쓰나), `add <ID>`(딸린 CSV·템플릿 폴더와 함께 꺼냄), `/edpm-doc <ID>`가 없으면 자동으로 꺼냄
- **경로 밖 전제는 막지 않음**: 워크스페이스에 없는 전제조건은 "이번 경로에 없음"(진행표 하단에 목록). 명시적 게이트(G-LEARN·G-EVIDENCE·G-STAGE·G-AI 등)가 요구하는 문서는 없으면 막고 꺼내라고 안내
- **경로 정하기**: `/edpm-prd path` — PRD를 읽고 필요한 산출물만 꺼냄(미성년 → E13, AI → E14·A10·A14·A06, 유료 → P01, 교과 → E11, 연구 PoC → D01, 효과 주장 → E16·E17), PRD frontmatter `path:`에 기록. 단계 "1.5 경로 정하기" 추가
- **프로토타입 병행**: PRD가 review가 되면 단계 안내가 스펙과 나란히 `/edpm-proto new`(PRD 9절의 정수)를 제안
- **스킬 33종 → 15종**: `edpm-start`(+init, blueprint), `edpm-doc`(+review, venture, feature, policy, proposal, content, list), `edpm-spec`(+qa), `edpm-ai`(ai-design + eval), `edpm-wiki`(ingest, query, lint, library, collect, promote), `edpm-brief`(+weekly, report, meeting). 기존 절차는 스킬 폴더의 참조 파일로 그대로 옮김(예: `edpm-doc/venture.md`). 명령 이름 변경: `/edpm-venture X` → `/edpm-doc venture X`, `/edpm-ingest` → `/edpm-wiki ingest`, `/edpm-eval` → `/edpm-ai eval` 등. `install.sh --upgrade`가 옛 스킬 폴더를 지우고 새 스킬을 넣음
- **기준 문서 한 곳**: README(사람용 기준, 재작성), `AGENTS.md`(에이전트용, 5절 스킬 표·6절 판정 규칙만), guide 02(체인·게이트 참조), guide 00(설치·문제 해결만, 재작성), guide 14(실전, 재작성). 문서에 산출물·스킬 개수를 쓰지 않음. 손으로 쓴 마스터 가이드 HTML과 `03.docs/_dashboard.md`(진행표와 중복) 삭제
- 대화형 설치에서 서비스 유형 질문 제거 (PRD 뒤 `/edpm-start blueprint detect`). blueprint apply는 필수 산출물을 꺼내는 방식으로
- A06 전제에 E14 추가(설계 전 평가 착수 방지), 새 워크스페이스의 끊긴 링크 0건
- G-SPEC: 운영 개선 과제의 F02(기능 단위 스펙)가 done이어도 제품 코드 허용 (바이브코딩 + 운영 개선). 출시 단계는 E15·E18이 보관함에 있어도 꺼내라고 안내. E06 파일명을 `E06_상세요구사항서.md`로 (제목과 일치)
- 회귀 테스트 4건(핵심 경로·보관함·경로 정하기·명시적 게이트, 설치 시 모드 문서, 출시 단계, F02 스펙 게이트) — 총 28건. 기존 테스트는 보관함 전체를 꺼낸 워크스페이스로 실행
- 기존 워크스페이스: `--upgrade` 후 PRD frontmatter에 `path:`가 없으면 상황판이 경로 정하기를 안내합니다. 이미 산출물을 다 갖고 있으면 `path: [기존]`처럼 적으면 됩니다

### Changed — sb-lowfi 기본 설치
- 화면설계 스킬 `sb-lowfi-pptx`·`sb-lowfi-figma`(rey-hailey/sb-lowfi)를 워크스페이스 설치와 `--upgrade` 때 기본으로 `~/.claude/skills`에 설치(이미 있으면 건너뜀, 네트워크가 없으면 플러그인 설치 안내). 건너뛰려면 `--no-sb-lowfi`, `--extras`는 sb-lowfi만 다시 설치, `--with-extras`는 호환용으로 남김. 대화형 설치의 변환 스킬 질문 제거. README·CLAUDE.md·guide 00·14·마스터 가이드·extras 안내 반영

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
