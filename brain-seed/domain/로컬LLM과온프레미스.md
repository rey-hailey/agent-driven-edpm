---
type: concept
status: draft
confidence: medium
sources: ["https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/", "https://docs.ollama.com/api/openai-compatibility", "https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md", "https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct", "https://ai.google.dev/gemma/terms", "https://huggingface.co/Qwen/Qwen3-8B", "https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503"]
verified: 2026-10-12
updated: 2026-10-12
tags: [AI, 로컬LLM, 온프레미스, 오픈모델, 라이선스, GPU, 양자화, 서빙, A10, A13]
---

# 로컬 LLM과 온프레미스 (M6)

> A10에서 "데이터를 밖으로 보낼 수 없을 때"의 생성 방식을 고르고, A12(GPU 원가)·A13(서빙 운영)을 쓸 때 참고. 로컬은 "무료"가 아니라 **사용량 비용을 고정비와 운영 부담으로 바꾸는 선택**이다.

## 핵심 요약

- 로컬을 택하는 이유: **데이터 위치 통제**(학생 글·음성·상담), **학교·기관 정책**(외부 전송 금지, 국외 이전 회피), **오프라인·학교망 제약**, **대규모 사용 시 단가**.
- 배포 형태 3가지: **기기 내(on-device)**, **학교·기관 서버(온프레미스)**, **사설 클라우드·VPC**(자사 클라우드 계정 안의 GPU).
- 서빙 스택 vLLM, Ollama, llama.cpp(llama-server)는 모두 **OpenAI 호환 API**를 제공한다 (아래 출처, verified: 2026-10-12). 그래서 클라우드 LLM과 같은 클라이언트 코드·같은 평가 스크립트로 비교할 수 있다 (`ai_eval.py --target local --endpoint ...`).
- 오픈 가중치 모델은 **라이선스가 제각각이고 자주 바뀐다**. 계열이 아니라 **사용할 정확한 모델 카드의 라이선스**를 확인한다.
- 같은 평가셋으로 클라우드 모델과의 **품질 격차**를 재고, 격차가 허용 범위인 기능에만 로컬을 쓴다.

## 상세

### 배포 형태

| 형태 | 예 | 장점 | 한계 |
|------|----|------|------|
| 기기 내 | 태블릿·전용 학습기에서 소형 모델 | 완전 오프라인, 데이터가 기기 밖으로 안 나감 | 모델 크기 제한, 기기 사양 편차, 배터리·발열, 업데이트 배포 |
| 학교·기관 서버 | 교육청·대학 전산실 GPU 서버 | 기관 정책 충족, 망 내부 | 설치·장애 대응·하드웨어 교체를 누가 하나, 기관별 버전 파편화 |
| 사설 클라우드·VPC | 자사 클라우드 계정 GPU 인스턴스 | 확장·운영 자동화, 국내 리전 선택 가능 | GPU 시간 비용, "외부 API는 아니지만 클라우드"인 점을 기관에 설명 필요 |

### 서빙 스택 (OpenAI 호환 API 확인)

| 스택 | 성격 | OpenAI 호환 |
|------|------|-------------|
| vLLM | GPU 서버용 고처리량 서빙 | Completions·Chat·Responses·Embeddings 등 엔드포인트 제공 (https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/, verified: 2026-10-12) |
| Ollama | 설치가 쉬운 로컬 실행기 | `http://localhost:11434/v1/`에서 OpenAI API의 일부(subset) 지원 (https://docs.ollama.com/api/openai-compatibility, verified: 2026-10-12) |
| llama.cpp (llama-server) | CPU·저사양 GPU·양자화 모델에 강함 | chat completions·responses·embeddings 호환 라우트 (https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md, verified: 2026-10-12) |

- "호환"은 **부분 호환**일 수 있다. 구조화 출력(JSON 스키마), 도구 호출, 스트리밍 동작을 실제로 시험한다.

### 하드웨어 규모 감 잡기 [가정: 근사치]

- 가중치 메모리 ≈ **파라미터 수 × 파라미터당 바이트**. FP16/BF16은 약 2바이트, 8비트 양자화 약 1바이트, 4비트 양자화 약 0.5바이트.
  - 예: 8B 모델 FP16 ≈ 16GB, 4비트 ≈ 4~5GB. 70B 모델 FP16 ≈ 140GB, 4비트 ≈ 35~40GB.
- 여기에 **KV 캐시**(문맥 길이 × 동시 사용자 수에 비례)와 런타임 여유분이 더해진다. 긴 문맥·동시 접속이 많으면 가중치보다 KV 캐시가 더 커질 수 있다.
- 양자화는 메모리·속도를 얻는 대신 품질이 떨어질 수 있다. **양자화 버전으로 평가셋을 다시 돌린다**.
- 실제 처리량(초당 토큰, 동시 요청 수)은 GPU·스택·모델·문맥 길이에 따라 크게 달라지므로 **부하 시험으로 측정**한다. 원가 계산은 [[domain/LLM비용과토큰과금]]의 GPU 원가 모델 참조.

### 오픈 가중치 모델 라이선스 (2026-10-12 확인분, 바뀔 수 있음)

| 계열 | 확인한 모델 | 라이선스 요지 | 상태 |
|------|-------------|---------------|------|
| Llama | Llama 3.3 70B Instruct | Llama 3.3 Community License. 월간 활성 사용자 7억 명 초과 시 Meta에 별도 허가 요청, 배포 시 "Built with Llama" 표시, 파생 모델 배포 시 이름이 "Llama"로 시작해야 함, 허용 사용 정책 준수 | verified: 2026-10-12 (https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) |
| Llama 4 등 다른 세대 | - | 세대마다 별도 라이선스 | [확인 필요] |
| Gemma (1~3n 등) | Gemma Terms of Use | 자체 약관(Apache 아님). 금지 사용 정책 포함, 재배포 시 사용 제한을 하위 계약에 포함, 위반 시 Google의 사용 제한 권리 | verified: 2026-10-12 (https://ai.google.dev/gemma/terms) |
| Gemma 4 | - | 약관 페이지가 "Gemma 4 license"로 Apache License 2.0 페이지를 연결 | verified: 2026-10-12 (https://ai.google.dev/gemma/apache_2), 모델 카드로 재확인 권장 |
| Qwen | Qwen3-8B | 모델 카드 apache-2.0 | verified: 2026-10-12 (https://huggingface.co/Qwen/Qwen3-8B). 일부 Qwen 모델은 자체 라이선스(Tongyi Qianwen 등) 사용 이력 [확인 필요: 모델별] |
| Mistral | Mistral Small 3.1 24B Instruct | 모델 카드 apache-2.0 | verified: 2026-10-12 (https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503). 다른 Mistral 모델은 연구용·상업 라이선스가 따로인 경우 있음 [확인 필요] |

- 확인 항목: 상업 이용, 사용자 수 상한, 표시 의무, 파생 모델 명명, 허용 사용 정책(미성년자 관련 조항 포함), 출력물 사용 제한, 준거법. **법무 검토 대상**이다.

### 한국어 성능

- 한국어를 지원한다고 밝힌 오픈 모델이 여럿 있고, 국내 기업·기관이 공개한 한국어 특화 모델도 있다 [확인 필요: 모델명·라이선스·현행 버전]. 공개 벤치마크보다 **자사 평가셋(교과 질의, 학생 구어체, 높임말·반말 정책)**으로 비교한다.
- 확인할 것: 높임말 일관성, 교과 용어 정확도, 영어 섞임, 토큰 효율(같은 문장이 몇 토큰인가).

### 품질 격차 시험

1. 같은 골든셋·E14 평가세트로 클라우드 기준 모델과 로컬 후보(원본·양자화)를 돌린다.
2. 합격률, 루브릭 점수, 안전 위반률, 지연 p95를 비교한다 ([[domain/AI평가메트릭과AB테스트]]).
3. 기능별로 허용 격차를 정한다: 학생 글 피드백 초안(교사 검토 있음)은 격차를 더 허용, 학생 직접 대화는 덜 허용.

### 운영 부담

- 모델 갱신·보안 패치, GPU 장애, 용량 계획, 모니터링, 기관별 설치본 버전 관리. 운영 인력이 없으면 VPC 관리형 서빙부터 검토한다 ([[domain/MLOps와LLMOps]]).

## 에듀테크 맥락

- **K-12 학생 데이터**: 학교·교육청이 외부 전송을 막거나 국외 이전을 꺼리면 M6가 사실상 유일한 생성 방식이 된다 ([[domain/아동개인정보보호]]).
- **학교망**: 교실 단위 오프라인·저대역이면 기기 내 또는 교내 서버.
- **교사 승인**: 로컬 모델 품질이 낮으면 교사 검토 단계를 둔 기능부터 적용한다.
- **조달**: 공공 납품은 설치형·보안 요구가 붙는 경우가 많다 [확인 필요: 사업별 RFP].

## 방식별 차이

| 비교 | M6 로컬 | M7 클라우드 |
|------|---------|-------------|
| 데이터 통제 | 높음 | 계약·리전·보존 정책에 의존 |
| 품질 | 모델 크기·양자화에 제한 | 대체로 높음 |
| 비용 구조 | 고정비(GPU·인력) | 사용량 비례 |
| 운영 | 자사 책임 | 공급사 책임 |

## 에듀테크 PM 적용

**체크리스트**

- [ ] A10: M6를 택한 이유(데이터·정책·망·비용)와 배포 형태를 적는다
- [ ] 후보 모델의 모델 카드 라이선스를 확인하고 법무 검토 결과를 남긴다
- [ ] 같은 평가셋으로 클라우드 대비 격차를 A06에 기록한다
- [ ] A12에 GPU 시간·인력 비용, A13에 서빙·갱신·장애 대응을 넣는다
- [ ] E13·P07에 데이터 위치와 처리 범위를 적는다

**관련 산출물**: A10, A11, A12, A13, A06, E13, P07, P09.

## 흔한 오해

- "오픈소스 모델이니 마음대로 써도 된다" — 많은 모델이 오픈소스 라이선스가 아닌 자체 약관이다.
- "로컬이면 비용이 0" — GPU와 사람 비용이 든다.
- "OpenAI 호환이면 그대로 바꿔 끼운다" — 기능별 호환 범위가 다르다.

## 관련 페이지

- [[domain/AI방식스펙트럼]] · [[domain/LLM비용과토큰과금]] · [[domain/모델선택과라우팅]] · [[domain/MLOps와LLMOps]] · [[domain/AI평가메트릭과AB테스트]] · [[domain/아동개인정보보호]] · [[domain/전용기기학습서비스]]

## 출처

- vLLM OpenAI 호환 서버: https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/ (verified: 2026-10-12)
- Ollama OpenAI 호환: https://docs.ollama.com/api/openai-compatibility (verified: 2026-10-12)
- llama.cpp server: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md (verified: 2026-10-12)
- Llama 3.3 모델 카드·라이선스: https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct (verified: 2026-10-12)
- Gemma 약관: https://ai.google.dev/gemma/terms, Gemma 4 라이선스 링크: https://ai.google.dev/gemma/apache_2 (verified: 2026-10-12)
- Qwen3-8B: https://huggingface.co/Qwen/Qwen3-8B, Mistral Small 3.1: https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503 (verified: 2026-10-12)
- 메모리 근사식: 일반 원리 [가정]
