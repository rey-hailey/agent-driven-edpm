---
type: regulation
status: draft
confidence: medium
sources: ["https://huggingface.co/Qwen/Qwen3-4B", "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE", "https://ai.google.dev/gemma/terms", "https://huggingface.co/stabilityai/sdxl-turbo", "https://stability.ai/license", "https://huggingface.co/hexgrad/Kokoro-82M", "https://huggingface.co/myshell-ai/MeloTTS-Korean", "https://huggingface.co/Supertone/supertonic-2", "https://huggingface.co/facebook/musicgen-small", "https://learn.microsoft.com/en-us/answers/questions/2088770/", "https://pixabay.com/service/license-summary/"]
verified: 2026-10-12
updated: 2026-11-03
tags: [AI, 라이선스, 로컬모델, 상업이용, 콘텐츠생성, A10, P07]
---

# 생성 AI 모델 상업 라이선스

**"무료"와 "상업 이용 가능"은 다르다.** 수익화하는 제품·콘텐츠(유료 서비스, 광고 수익 영상, 교재)에 쓰기 전에 모델 가중치와 자산(음원·폰트·이미지)의 라이선스를 확인한다. 아래는 2026-10-12 확인 기준이며 라이선스는 바뀐다. 쓰기 전에 원문을 다시 확인하고 A10 2.1절에 확인 일자와 함께 기록한다.

| 단계 | 상업 이용 가능 (조건 확인) | 사용 불가·주의 |
|------|---------------------------|----------------|
| 텍스트 (로컬) | Qwen3 (Apache-2.0), Gemma 3 (Gemma Terms, 금지 용도 정책), Llama 3.x (Community License, 월 사용자 7억 미만·표기 요구) | Qwen2.5-3B (qwen-research, 상업 이용 시 별도 라이선스) |
| 이미지 | FLUX.1 schnell (Apache-2.0), SD 1.5·SDXL 1.0 (CreativeML OpenRAIL-M, 용도 제한), SD 3.5 (Stability Community License, 연매출 100만 달러 미만) | FLUX.1 dev (가중치 비상업), SDXL-Turbo (라이선스 모호) |
| 음성 (영어 등) | Kokoro-82M (Apache-2.0, 한국어 없음), Piper (엔진 GPL, **음성마다 라이선스 다름**) | Coqui XTTS-v2 (CPML 비상업, 판매자 폐업), F5-TTS (가중치 CC-BY-NC-4.0), macOS `say` 음성 (개인·비상업 조항), edge-tts (Azure 없는 상업 이용은 약관 위반 소지) |
| 음성 (한국어) | MeloTTS-Korean (MIT), Supertonic (모델 OpenRAIL-M, 기계 생성 고지 조건 확인) | — |
| 음악 | 절차 생성(직접 작성 코드), YouTube 오디오 보관함 (트랙별 조건), Stable Audio Open (연매출 100만 달러 미만) | MusicGen (가중치 CC-BY-NC-4.0), Pixabay 일부 트랙 (Content ID 등록 → 클레임 가능) |

## 판단 순서

1. 가중치 라이선스 원문을 본다 (코드 라이선스와 다를 수 있음 — 예: F5-TTS 코드 MIT, 가중치 비상업).
2. 매출·사용자 상한, 금지 용도, 표기 의무가 있는지 본다.
3. 출력물 권리 조항을 본다 (일부 약관은 출력물 권리를 주장하지 않음).
4. 아동 대상이면 금지 용도 정책과 플랫폼 정책(앱스토어·YouTube)을 함께 본다.
5. A10 2.1절에 대상·라이선스·확인일을 남기고 180일마다 재확인한다.

## 에듀테크에서 자주 생기는 실수

| 실수 | 결과 | 대신 |
|------|------|------|
| 데모에서 쓴 비상업 모델을 그대로 제품에 씀 | 출시 후 교체·재생성 비용 | 프로토타입 단계부터 상업 가능 모델로 (V01 빌드 환경) |
| 무료 음원 사이트 트랙을 영상에 씀 | Content ID 클레임, 수익 몰수 | 절차 생성 또는 라이선스가 기록된 트랙만 |
| OS 내장 음성으로 교재 낭독 파일 판매 | 약관 위반 | 상업 가능 TTS (Kokoro, MeloTTS 등) |

관련: [[domain/AI저작권정책]] · [[domain/AI방식스펙트럼]] · [[domain/로컬LLM과온프레미스]]
