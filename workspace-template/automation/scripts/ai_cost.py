#!/usr/bin/env python3
"""EdPM AI 비용 계산기 (A12 AI비용·과금설계서)

학습자 수·사용량·요청당 토큰·모델 라우팅 비율·캐시 적중률로 월 원가와 학습자 1인당 원가를 계산한다.
클라우드 모델은 토큰 단가(model_prices.json), 로컬 모델은 GPU 시간 비용(시간당 단가 ÷ 실제 처리량)으로 계산한다.
규칙·NLP·FAQ로 처리되는 요청(deflection)은 AI 비용 0으로 본다.

사용:
  python automation/scripts/ai_cost.py --config 03.docs/A.AI/ai_cost_config.json
  python automation/scripts/ai_cost.py --example        # 예시 설정 출력

설정 예 (JSON):
{
  "learners": 5000, "active_ratio": 0.6, "sessions_per_week": 3, "requests_per_session": 8,
  "deflection_ratio": 0.3,
  "routes": [
    {"name": "쉬운 질문", "share": 0.6, "model": "claude-haiku-5-5", "input_tokens": 1500, "output_tokens": 300, "cache_hit": 0.0},
    {"name": "힌트 해설", "share": 0.3, "model": "claude-sonnet-5-5", "input_tokens": 3000, "output_tokens": 500, "cache_hit": 0.5},
    {"name": "민감 데이터", "share": 0.1, "model": "local-example", "input_tokens": 2000, "output_tokens": 400}
  ],
  "fixed_monthly_usd": {"vector_db": 50, "monitoring": 30},
  "price_per_learner_month_usd": 9.0
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WEEKS_PER_MONTH = 52 / 12
EXAMPLE = {
    "learners": 5000, "active_ratio": 0.6, "sessions_per_week": 3, "requests_per_session": 8,
    "deflection_ratio": 0.3,
    "routes": [
        {"name": "쉬운 질문", "share": 0.6, "model": "claude-haiku-5-5", "input_tokens": 1500, "output_tokens": 300, "cache_hit": 0.0},
        {"name": "힌트 해설", "share": 0.3, "model": "claude-sonnet-5-5", "input_tokens": 3000, "output_tokens": 500, "cache_hit": 0.5},
        {"name": "민감 데이터", "share": 0.1, "model": "local-example", "input_tokens": 2000, "output_tokens": 400},
    ],
    "fixed_monthly_usd": {"vector_db": 50, "monitoring": 30},
    "price_per_learner_month_usd": 9.0,
}


def request_cost(route: dict, price: dict) -> float:
    inp, out = route["input_tokens"], route["output_tokens"]
    if price["type"] == "cloud":
        hit = route.get("cache_hit", 0.0)
        cached_price = price.get("cached_input")
        if cached_price is None:
            hit = 0.0  # 캐시 단가를 모르면 절감을 가정하지 않음
            cached_price = price["input"]
        return (inp * (1 - hit) * price["input"] + inp * hit * cached_price + out * price["output"]) / 1e6
    effective_tps = price["throughput_tokens_per_sec"] * price.get("utilization", 1.0)
    seconds = (inp + out) / effective_tps
    return seconds / 3600 * price["gpu_hourly_usd"]


def main() -> int:
    ap = argparse.ArgumentParser(description="EdPM AI 비용 계산기")
    ap.add_argument("--config", type=Path)
    ap.add_argument("--prices", type=Path, default=Path(__file__).with_name("model_prices.json"))
    ap.add_argument("--example", action="store_true", help="예시 설정 JSON 출력")
    args = ap.parse_args()
    if args.example:
        print(json.dumps(EXAMPLE, ensure_ascii=False, indent=2))
        return 0
    if not args.config:
        ap.error("--config 또는 --example 이 필요합니다")
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    prices = json.loads(args.prices.read_text(encoding="utf-8"))["models"]

    shares = sum(r["share"] for r in cfg["routes"])
    if abs(shares - 1.0) > 1e-6:
        raise SystemExit(f"routes의 share 합이 1이 아닙니다: {shares}")
    active = cfg["learners"] * cfg["active_ratio"]
    requests = active * cfg["sessions_per_week"] * WEEKS_PER_MONTH * cfg["requests_per_session"]
    ai_requests = requests * (1 - cfg.get("deflection_ratio", 0.0))

    rows, variable = [], 0.0
    for r in cfg["routes"]:
        if r["model"] not in prices:
            raise SystemExit(f"가격표에 없는 모델: {r['model']} ({args.prices})")
        per_req = request_cost(r, prices[r["model"]])
        n = ai_requests * r["share"]
        cost = per_req * n
        variable += cost
        rows.append((r["name"], r["model"], prices[r["model"]]["type"], n, per_req, cost))
    fixed = sum(cfg.get("fixed_monthly_usd", {}).values())
    total = variable + fixed
    per_active = total / active if active else 0
    per_learner = total / cfg["learners"] if cfg["learners"] else 0

    print("# AI 월 원가 추정\n")
    print(f"- 활성 학습자 {active:,.0f}명 / 월 요청 {requests:,.0f}건 (규칙·FAQ 처리 {cfg.get('deflection_ratio', 0):.0%} 제외 → AI 요청 {ai_requests:,.0f}건)\n")
    print("| 경로 | 모델 | 방식 | 월 요청 | 요청당 원가(USD) | 월 원가(USD) |")
    print("|------|------|------|---------|------------------|--------------|")
    for name, model, typ, n, per_req, cost in rows:
        print(f"| {name} | {model} | {typ} | {n:,.0f} | {per_req:.5f} | {cost:,.2f} |")
    print(f"| 고정비 | {', '.join(cfg.get('fixed_monthly_usd', {}).keys()) or '-'} | | | | {fixed:,.2f} |")
    print(f"| **합계** | | | | | **{total:,.2f}** |\n")
    print(f"- 활성 학습자 1인당 월 원가: {per_active:.3f} USD")
    print(f"- 전체 학습자 1인당 월 원가: {per_learner:.3f} USD")
    price = cfg.get("price_per_learner_month_usd")
    if price:
        margin = 1 - per_learner / price
        print(f"- 학습자당 월 가격 {price} USD 대비 AI 원가 비중: {per_learner / price:.1%} (AI 원가 차감 후 남는 비율 {margin:.1%})")
    print("\n> 가격은 model_prices.json 기준 참고값입니다. 로컬 모델 원가는 GPU 단가·처리량·가동률 가정에 크게 좌우되므로 A12에 근거를 적습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
