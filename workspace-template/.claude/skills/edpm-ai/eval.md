# edpm-ai eval

실행기는 `automation/scripts/ai_eval.py`입니다. 이 스크립트는 Claude API를 호출하므로 **비용이 듭니다.** 항상 `--dry-run`으로 호출 수를 보여주고 사람이 승인한 뒤 실행합니다.

## 준비

| 항목 | 위치 |
|------|------|
| 시스템 프롬프트 | `03.docs/A.AI/prompts/system_vN.md` (`/edpm-ai prompt-export`로 분리) |
| 골든셋 (정답형: 질문 한 번 → 기대 답·근거, 주로 구성 요소 `근거`) | `03.docs/A.AI/골든셋.csv` |
| 시나리오셋 (시나리오형: 사전 상태와 여러 턴 → 기대 행동, 구성 요소 `학습자상태`·`데이터조회`·`생성물`) | `03.docs/A.AI/시나리오셋.csv` |
| 교육적 평가세트 | `03.docs/3.설계/E14_평가세트.csv` |
| 패키지 | `pip install anthropic` |
| 인증 | `ANTHROPIC_API_KEY` 환경변수 또는 `ant auth login` 프로필 (키를 파일에 쓰지 않음) |

평가 데이터에는 가상·가명 데이터만 씁니다. 스크립트는 전화번호·이메일·주민번호 패턴이 보이면 멈춥니다. `비고`가 `예시`로 시작하는 템플릿 행은 실제 행이 있으면 건너뜁니다.

## run <세트>

```bash
python automation/scripts/ai_eval.py --set 03.docs/A.AI/골든셋.csv \
  --system 03.docs/A.AI/prompts/system_v1.md --dry-run      # 호출 수 확인
python automation/scripts/ai_eval.py --set 03.docs/A.AI/골든셋.csv \
  --system 03.docs/A.AI/prompts/system_v1.md --limit 5      # 소량 먼저
python automation/scripts/ai_eval.py --set 03.docs/A.AI/골든셋.csv \
  --system 03.docs/A.AI/prompts/system_v1.md                # 전체
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--model` | claude-opus-5-5 | 평가 대상 응답 모델 |
| `--judge-model` | claude-opus-5-5 | 채점 모델 |
| `--effort` | medium | 응답·채점 effort |
| `--context` | 없음 | P3 노코드 점검: 지식 문서를 검색 없이 통째로 붙임 |
| `--target` | claude | `claude` / `local`(OpenAI 호환 로컬 서버, `--endpoint`) / `cmd`(자체 규칙·NLP·검색 시스템, `--cmd`) |
| `--judge` | llm | `llm`(루브릭 채점) / `exact`(정형 답: 기대답변 포함·정규식 일치, 금지어 검사, LLM 호출 없음) |
| `--label` | 없음 | 결과 파일·요약에 붙일 비교용 이름 |
| `--limit` | 전체 | 앞에서 N행 |

결과: `05.outputs/eval_YYYYMMDD_HHMM.csv`(행별 응답·점수·실패 유형)와 같은 이름의 `.md` 요약(합격률, 평균 점수, 실패 유형 분포, 추정 비용).

## methods — AI 방식 비교 (A10·A11)

같은 평가셋을 방식별로 실행해 합격률·점수·지연 p50/p95·비용을 나란히 비교합니다.

```bash
python automation/scripts/ai_eval.py --set 03.docs/A.AI/골든셋.csv --system 03.docs/A.AI/prompts/system_v1.md --label cloud
python automation/scripts/ai_eval.py --set 03.docs/A.AI/골든셋.csv --system 03.docs/A.AI/prompts/system_v1.md \
  --target local --endpoint http://localhost:11434/v1 --model <로컬 모델> --label local
python automation/scripts/ai_eval.py --set 03.docs/A.AI/의도분류셋.csv --system 03.docs/A.AI/prompts/none.md \
  --target cmd --cmd "python automation/scripts/<분류기>.py" --judge exact --label rules
```

로컬·자체 시스템은 응답 비용이 0으로 나오므로 GPU·운영비는 `ai_cost.py`로 따로 계산합니다. 정형 답(의도 분류, 단답형 채점)은 `--judge exact`로 채점해야 공정합니다.

## compare <프롬프트A> <프롬프트B>

같은 세트를 두 프롬프트(또는 `--model`을 바꿔 두 모델)로 실행하고, 행별로 합격이 바뀐 항목(좋아진 것, 나빠진 것)과 평균 점수 차이를 표로 보여줍니다. 전체 합격률만 보지 않고 **나빠진 행**을 먼저 보고합니다. 모델 비교일 때는 비용·지연도 함께 적습니다.

## triage

불합격 행을 실패 유형별로 묶고 원인과 고칠 곳을 제안합니다.

| 실패 유형 | 주로 고칠 곳 |
|-----------|--------------|
| 검색실패 | A01 지식 소스 누락, A02 필터·청크 |
| 생성오류 | A03 근거 사용 지시, 모델 선택 |
| 교육규칙위반 | A03 힌트 사다리·정답 금지 규칙, E14 GR |
| 안전위반 | A03 고정 응답, E13 (d) |
| 기억오류 | A04 기억 정책·추출 프롬프트 |
| 도구데이터오류 | A05 도구 정의·권한, B03 데이터 |

LLM 채점은 틀릴 수 있습니다. 불합격 건과 점수 3점 이하 경계 사례는 사람이 다시 보고, 채점이 틀렸으면 세트의 `채점기준`을 더 구체적으로 고칩니다.

## report → A06

최근 결과 파일을 읽어 `03.docs/A.AI/A06_AI평가결과보고서.md`를 채웁니다: 평가 대상(프롬프트 버전, 모델, 지식베이스 버전), 세트별 건수, 지표별 결과(스크립트 수치 그대로), 실패 분석, 모델 비교, **G-AI 판정**(E14 합격 기준 충족 여부). 실체 검증: 골든셋 30건 이상 또는 시나리오셋 10건 이상, 결과 파일 경로 기재.

## log

`## [YYYY-MM-DD] eval | {세트} {프롬프트 버전} — 합격 N/M, 비용 $N`
