# CHANGELOG

Agent Driven EdPM 변경 이력입니다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/), 버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

- MAJOR: 폴더 체계·층 구조·흐름 게이트 변경
- MINOR: 산출물·게이트·스킬·스크립트 추가·삭제
- PATCH: 템플릿 문구, 오타, 설명 보완

## [Unreleased]

### Changed — 출처 표기 (과정 저작권자 동의 조건)
- LICENSE 끝과 README 8절(주의, 라이선스와 출처)에 출처: 영감을 받은 것(문서 체인·게이트 체크 방식), 새로 만든 것, 포함하지 않는 것, MIT는 이 저장소 내용에만 적용
- README에 출처 한 줄: Agent PM 과정(AP-Framework)의 문서 체인·게이트 체크 방식에서 출발해 에듀테크용으로 확장, 공식 배포판이 아닌 개인 프로젝트
- `.gitignore`에서 EdPM이 쓰지 않는 과정 전용 키 파일 줄 제거
- CLAUDE.md 출처 규칙과 회귀 테스트: 과정 템플릿·프롬프트 번호·교안 원문을 넣지 않고, AP·과정 이름은 README 출처 줄에만

### Added — 프레임워크 CI
- `.github/workflows/tests.yml`: PR과 main push마다 회귀 테스트(`tests/`)를 Python 3.10·3.13에서 실행. 이후 변경은 브랜치 → PR → 테스트 통과 후 합침

### Fixed
- 루트 `.gitignore`의 `.vscode/`가 `workspace-template/.vscode/`까지 막아 GitHub에서 받은 설치본에 에디터 설정(권장 확장, holdout 검색 제외)이 빠지던 문제. 루트만 무시하도록 변경 (CI가 발견)

### Added — 출시 후 현행화와 G-ASBUILT
- 원칙: 출시 전에는 스펙이 기준, 출시 후에는 배포된 코드가 기준이고 문서가 따라감 (AGENTS.md 1.1, guide 09)
- `automation/scripts/edpm_asbuilt.py`: 제품 코드의 화면 경로(Next.js `app/`·`pages/`, route group·병렬 슬롯 제외), API 경로·메서드(`route.*`, `pages/api`, Express·FastAPI 라우터), 기능 ID(F-001)를 E10 8절 `주소`·B02 2절·E09 1절(후속 릴리스 제외)·F02와 대조. `scan`, `record <릴리스>`(`05.outputs/현행화/<릴리스>_<날짜>.md`: 요약·차이·판정 칸·일치·현행화 이력), `--no-code "사유"`, `status`. `[id]`·`{id}`·`:id`·구체 값은 같은 자리로 봄
- 게이트 **G-ASBUILT**: E15가 done이면 그 뒤 현행화 기록이 있고 `{판정}`이 남지 않아야 M05·E20 완료. 상황판·대시보드에 "출시 후 현행화" 표시
- `/edpm-change asbuilt`(판정: 문서 갱신 → 변경 전파 / 결함 → defects / 의도된 차이 → 사유), AGENTS.md 2절 "제품 코드 위치", qa smoke 6단계, E15·M05·E20·F04 체크리스트, guide 02·09·13, README
- 회귀 테스트 1건 — 총 41건

### Added — 변경 전파: 하나를 고치면 연결된 곳까지
- `automation/scripts/edpm_ripple.py`: 산출물 본문이 바뀌면 그 문서를 `requires`로 쓰는 바로 아래 문서와 같은 ID(REQ·F·SCR·LO·EV·M …, 과제 폴더 안에서는 US·T·AC·IF도)를 쓰는 문서를 "전파 대기"로 기록 (`.edpm/ripple.json`). 대기 문서를 고치면 풀리고 그 하위로 한 단계씩 이어짐. `<문서>`로 전체 범위(하위 산출물·같은 ID·테스트·코드·WBS·화면), `pending`, `ack <문서> <사유>`, `wbs [--write]`(전파 작업 `WP-R.n`을 M02_WBS.csv에). 상태만 바꾼 저장·손대지 않은 템플릿·n/a 제외
- 훅: PostToolUse `edpm_ripple.py record`(변경 전파를 에이전트에게 알림), SessionStart `snapshot`. 상황판·대시보드 주의에 "변경 전파 대기"
- 스킬 `/edpm-change`: 전파 처리(체인 순서대로 갱신·ack·결정, done 문서 재승인, 테스트 고정 해제 절차, WBS 반영), `screen <SCR-ID>`(스테이징·코드에서 먼저 바뀐 화면을 E10·스펙으로 역반영 — 배치·문구는 E10, 규칙은 PM 승인 후 AC), `archive <릴리스>`(릴리스 화면 아카이브, Figma는 선택 기록)
- `edpm_screens.py --archive <릴리스> [--base URL] [--capture]`: `05.outputs/화면아카이브/<릴리스>_<날짜>/index.md`와 화면별 캡처(Playwright가 있으면 직접). E10 8절에 `- 주소:` 키
- `/edpm-spec qa smoke` 6단계 화면 아카이브, `/edpm-prd update`·`/edpm-wbs impact`가 전파 범위를 씀. AGENTS.md·README·guide 13
- **업그레이드 주의**: 훅이 늘어 `.claude/settings.json`이 바뀌었습니다. `install.sh --upgrade`는 기존 설정을 덮지 않고 `settings.new.json`을 두므로, 합쳐야 변경 전파 훅이 켜집니다 (`edpm_ripple.py` 명령은 합치기 전에도 쓸 수 있음)
- 회귀 테스트 2건 — 총 40건

### Changed — 개선 과제 유형: 학습 / 사용성 / 운영
- 모든 개선이 교육적 효과를 노리지는 않으므로 과제마다 유형을 정함 (F01 0절, frontmatter `task_type`). 판정 질문: "학습자의 학습 활동이나 평가·피드백 결과를 바꾸는가?" 제출 확인 단계 제거·힌트 한 번에 펼치기처럼 학습 흐름에 닿으면 학습
- 점검기 G-MEASURE: F01은 `task_type`(학습·사용성·운영)이 있어야 완료, 학습 과제의 F02는 학습 지표 행(기준선·목표·SQL)이 있어야 완료. 사용성·운영 과제는 학습 지표 `n/a`로 통과. `n/a` 행은 지표 행으로 세지 않음. **업그레이드 주의**: 기존 워크스페이스의 F01은 `task_type`을 적어야 done으로 올라감
- F02 학습 지표 "필수" → 학습 과제만 필수, 사용성 지표 예시 추가. F03은 사용성·운영 과제면 단계 출시·롤백 위주로 짧게, 윤리 점검은 학습 과제나 학습자를 나눠 비교할 때만
- 개선백로그 유형 열, 교육적 효과는 학습 과제만 매기고 사용성·운영은 `n/a`(중립값 3으로 계산). 사용성 예시 FI-012(제출 클릭 3번 → 1번)
- E06 요구사항 표에 유형 열: 학습 REQ는 LO 추적, 사용성·운영 REQ는 PB·IN 추적과 E09 운영·지원 기능
- guide 09에 "일하는 방식이 달라도: 0→1, 워터폴, 애자일" 절. guide 02·14, AGENTS.md 문구 정리
- E09 스펙은 첫 릴리스(R1) 기능만 상세히, 다음 릴리스 기능은 기능 목록에 `릴리스` 열과 상태 `후속 릴리스`로만. 출시(파일럿 포함) 후 F00을 쓰고 후속 기능은 F 트랙 F02로 — 0→1을 짧게 밟고 출시 후 애자일로 이어짐. 대시보드 스펙 추적과 `/edpm-spec check`는 후속 릴리스 기능을 끊긴 추적으로 보지 않음. 게이트(G-SPEC)는 그대로
- 회귀 테스트 1건

### Added — 리서치, 팀 알림, CI와 배포 후 점검
- `/edpm-wiki research <질문>`: 하위 질문 → 웹 검색·원문 읽기 → 출처 등급(1차·2차·3차) → 자료실에 원본 요약(URL·접근일·등급) → 위키 종합(상충 근거, verified) → N01·E04·PRD 2절로. 수치는 1차 출처가 있을 때만 사실로
- `automation/scripts/edpm_notify.py` + `/edpm-brief notify`: 상황판·주간보고·사건을 Slack·Teams 웹훅으로 (기본 미리보기, `--send`로 전송, 보낼 내용의 식별 정보 검사, 전송은 권한 확인). `.github/workflows/edpm-brief.yml`: 평일 아침 상황판 자동 발송 (Claude 없이, 웹훅 비밀값이 있을 때만)
- `edpm_check.py ci [--base]` + `.github/workflows/edpm-ci.yml`: 훅을 거치지 않은 변경도 게이트 미충족 done·식별 정보·frontmatter 오류·고정 테스트 수정을 막고, 제품 코드가 있으면 테스트 실행
- `/edpm-spec qa smoke <URL>`: 배포 후 핵심 흐름·에듀테크 점검(동의 전 잠금, 결제 테스트 모드, 학습자 화면 광고·외부 링크, 식별 정보 노출, AI 거절·대체)·기본 품질
- 회귀 테스트 2건 — 총 37건

### Changed — 화면 지도와 실무형 화면설계서(sb-lowfi) 역할 분담, README를 "PM 엔진 + 에듀테크 팩"으로
- 자동 HTML은 **화면 지도**(점검용)로: 전체 목록·상태·끊긴 이동. 보여주는 화면설계서는 sb-lowfi가 그림
- `edpm_screens.py --sb-md [경로]`: E10에서 sb-lowfi-pptx 입력 md(화면 목록 + 화면별 메타 표·레이아웃·번호 붙은 UI 컴포넌트·상태별 화면·처리 규칙) 생성 (기본 `05.outputs/화면설계서.md`). `05.outputs/`에 sb-lowfi 결과 HTML이 있으면 화면 지도가 화면마다 링크
- README: PM 엔진(어느 회사에서나)과 에듀테크 팩을 나눠 소개
- 회귀 테스트 보강

### Added — 화면설계서: 모든 화면을 E10에서 자동으로
- E10 8절 "화면별 구성"(화면마다 블록 하나: 영역 · 항목, `[라벨 → SCR-ID]` 이동 버튼, `[라벨]` 버튼, `(입력: 라벨)`, 진입·설명·연결). 7절을 "화면설계서·와이어프레임 산출"로 (자동 생성 / 회의용 PPTX·Figma는 sb-lowfi / 정수 흐름만 V 트랙)
- `automation/scripts/edpm_screens.py` + `screens_template.html` → `.edpm/screens.html`: 화면 지도(역할별 썸네일, 나가는 화면), 화면 보기(플랫폼별 프레임, 기본·빈·로딩·오류·동의 없음·오프라인·권한 없음 탭과 E10 3절 문구, 이동 버튼으로 실제 화면 이동, 들어오고 나가는 곳, 연결 기능·인수조건, 접근성), "설계 보기"로 영역 주석, 구성 없음·상태 빠짐·끊긴 이동 표시, `#SCR-ID`로 바로 열기. 대시보드와 함께 갱신, 대시보드에 "화면" 탭
- 원칙: 화면마다 프로토타입을 만들지 않는다 — 화면 전체는 문서에서 자동으로, 높은 충실도는 PRD 9절 정수에만
- 회귀 테스트 1건 — 총 35건

### Added — 대시보드
- `automation/scripts/edpm_dashboard.py` + `dashboard_template.html`: 워크스페이스 상태를 `.edpm/dashboard.html` 한 장으로. 왼쪽(지금 단계·흐름 막대·다음 명령 복사, PRD 명확도, 진행 요약, WBS 달력, 최근 파일), 가운데(위키·산출물 지식 그래프: 도메인 지식은 AI·규제·표준·IA·화면·학습과학·평가·비즈니스·운영 군집, 회사·학습자·리서치·시장·결정·교육과정, 가운데 산출물은 상태별 색, 링크·전제조건 연결), 오른쪽(주의, 경로 문서, 스킬 검색·명령 복사, 프로토타입·결정, 위키 log). 점을 누르면 Antigravity에서 파일이 열림(`EDPM_EDITOR_URL`로 변경). 외부 라이브러리·네트워크 없음, 보기 전용, 판정은 점검기와 같음
- **가운데를 탭 세 개로**: 여정 보드(기본 — 리서치·PRD·학습 성과·요구사항·스펙·설계·구현·검증·출시·효과 칸에 문서 카드, 지금 단계 강조, 아래에 프로토타입·운영 개선 과제(F01~F04 진행)·결정·관리·사업 줄), 스펙 추적(E09·F02 기능별 REQ·유저스토리·인수조건·상태 흐름·작업·테스트, 끊긴 곳: REQ 없음·작업 없는 AC·테스트 없는 작업·테스트 파일 없음), 지식 그래프. 주소 해시(`#trace`)로 탭 지정. 보드와 겹치던 오른쪽 경로 문서·프로토타입 카드 제거
- **다음 할 일**: 보드 카드마다 점검기 판정을 명령 하나로(착수 가능 → 그 문서 명령, 대기 → 막고 있는 문서 명령, 검토 중 → 이해관계자 검토, 프로토타입 → plan·build·test·decide, 운영 개선 과제 → 지금 차례 F 문서). 상황판 첫 할 일과 같은 카드에 "지금 할 일" 표시, PRD 때문에 막힌 카드는 명령 대신 안내만. 카드는 옮기지 않음(상태는 문서와 훅이 정함)
- 편집기 링크: macOS에 `Antigravity IDE.app`(에디터, `antigravity-ide://`)과 별도 앱 `Antigravity.app`(`antigravity://`)이 함께 있으면 링크가 IDE가 아닌 앱으로 가던 문제 — 설치된 편집기를 Antigravity IDE → Cursor → VS Code → Antigravity 순서로 찾음, `EDPM_EDITOR_URL`로 지정 가능. 설치 스크립트의 사전 점검·바로 열기도 IDE 우선
- SessionStart·PostToolUse(저장 후) 훅이 다시 만들고, 열어 둔 화면은 조용할 때 다시 읽음. `/edpm-brief dashboard`, 설치 직후 생성, `.gitignore`에 생성물 제외
- 회귀 테스트 1건 — 총 34건

### Added — 엉뚱한 것을 만들지 않게: 명확도·개념·숨긴 평가·아직 모르는 것
개념 참고: [Q00/ouroboros](https://github.com/Q00/ouroboros)(MIT)의 모호도 게이트·존재론 질문·숨긴 채점 기준·Wonder 루프. 코드는 가져오지 않고 EdPM 방식으로 구현.
- **G-CLEAR 명확도 게이트**: `edpm_check.py clarity` — PRD(목표·근거·대상·성공 기준·핵심 개념·제약)와 F01(문제·근거·성공 기준·기존 서비스 맥락)의 표 채움으로 모호도를 계산, 0.3을 넘으면 PRD review 전환(훅)과 F01 done을 막음. 단계 1이 모호도를 보여주고, `/edpm-prd review`가 같은 차원을 루브릭으로 읽고 채울 질문을 제안
- **핵심 개념 정의**: PRD 5.1절(계산 가능한 정의·경계·이어지는 곳), F01 6.1절 "지금의 규칙과 개념". PRD 인터뷰가 "이 말은 정확히 무엇인가"를 묻고, E09 입출력 계약이 정의를 이어받음
- **holdout 평가셋**: 파일 이름에 holdout이면 훅이 읽기·검색·수정·셸 열람을 막고(`.ignore`·`.vscode` 검색 제외 포함), `ai_eval.py --holdout`은 합격률·평균 점수만 출력. A06에 일반·holdout 점수를 나란히
- **인수조건 테스트 고정**: `/edpm-spec build`가 테스트를 먼저 커밋, 커밋된 `tests/` 수정은 훅이 막음. 스펙 변경 시 `.edpm/test-unlock`에 경로·사유(상황판 표시)
- **아직 모르는 것**: V03·F04·E20에 "아직 모르는 것(다음 사이클로)" 표, 넘긴 곳이 빈 항목을 상황판이 표시
- 훅 matcher에 Read·Grep·Bash 추가, 회귀 테스트 5건 — 총 33건

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
