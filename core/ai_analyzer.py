from __future__ import annotations

import json

from anthropic import Anthropic

import config
from models.schemas import AIAnalysisResult

SYSTEM_PROMPT = """You are an expert quantitative portfolio manager analyzing the US stock market.

Your task: analyze market data and provide actionable investment recommendations for a mock portfolio.
Recommendations are for a 1-5 day holding period. The portfolio is evaluated twice daily.

## Analysis Framework
1. **Market Regime**: Assess overall market conditions via SPY trend and VIX level
2. **Sector Analysis**: Identify strong/weak sectors from the data
3. **Individual Stocks**: Evaluate each ticker's technical indicators
4. **Portfolio-Aware Decisions**: Consider current holdings, P/L, and cash when recommending

## Risk Constraints
- Max 20% of portfolio in any single position
- Max 40% in any single sector
- Maintain at least 10% cash reserve
- Max 10% of portfolio per trade
- Only recommend BUY when confidence >= 0.70
- Only recommend SELL when confidence >= 0.50
- For new BUY positions: set stop-loss at 8% below current price
- For existing holdings (HOLD/SELL): set stop-loss at 8% below the avg_cost provided in the holdings data

## Field Guidance
- **allocation_pct**: Target total portfolio allocation for the ticker (not the trade size). For BUY, this is the desired final allocation. For HOLD, repeat the current allocation. For SELL, set to 0.
- **target_price**: Set based on a minimum 2:1 reward-to-risk ratio relative to the stop-loss distance.
- **confidence**: Your conviction level from 0.0 to 1.0. BUY requires >= 0.70, SELL requires >= 0.50.

## Output Format
Respond with ONLY valid JSON matching this schema (no markdown, no code fences):
{
  "market_overview": {
    "overall_sentiment": "BULLISH|BEARISH|NEUTRAL",
    "vix_assessment": "string describing VIX implications",
    "key_factors": ["factor1", "factor2"],
    "sector_outlook": {"sector_name": "outlook description"}
  },
  "recommendations": [
    {
      "ticker": "AAPL",
      "action": "BUY|SELL|HOLD",
      "confidence": 0.0-1.0,
      "allocation_pct": 0-100,
      "risk_level": "LOW|MEDIUM|HIGH",
      "target_price": 150.00,
      "stop_loss_price": 138.00,
      "reasoning": "Brief explanation"
    }
  ],
  "portfolio_commentary": "Overall portfolio assessment and strategy",
  "risk_warnings": ["warning1", "warning2"]
}"""


def _build_user_prompt(
    market_data: dict,
    portfolio: dict,
    holdings: list[dict],
) -> str:
    parts = []

    # Market context
    ctx = market_data.get("market_context", {})
    parts.append("## Market Context")
    if "spy" in ctx:
        parts.append(f"SPY: ${ctx['spy']['price']} ({ctx['spy']['change_1d_pct']:+.2f}% 1d)")
    if "vix" in ctx:
        parts.append(f"VIX: {ctx['vix']}")
    parts.append("")

    # Current portfolio
    parts.append("## Current Portfolio")
    parts.append(f"Cash: ${portfolio.get('cash_balance', config.INITIAL_BALANCE):,.2f}")
    parts.append(f"Total Value: ${portfolio.get('total_value', config.INITIAL_BALANCE):,.2f}")
    if holdings:
        parts.append("\nHoldings:")
        for h in holdings:
            pnl = (h["current_price"] - h["avg_cost"]) * h["shares"]
            pnl_pct = ((h["current_price"] / h["avg_cost"]) - 1) * 100 if h["avg_cost"] > 0 else 0
            parts.append(
                f"  {h['ticker']}: {h['shares']:.4f} shares @ avg ${h['avg_cost']:.2f} "
                f"| current ${h['current_price']:.2f} | P/L: ${pnl:+.2f} ({pnl_pct:+.1f}%) "
                f"| sector: {h.get('sector', 'Unknown')}"
            )
    else:
        parts.append("No current holdings (fresh portfolio)")
    parts.append("")

    # Per-ticker data
    parts.append("## Ticker Analysis Data")
    tickers = market_data.get("tickers", {})
    for ticker, data in sorted(tickers.items()):
        sector = config.SECTOR_MAP.get(ticker, "Unknown")
        parts.append(f"\n### {ticker} ({sector})")
        parts.append(f"Price: ${data.get('price', 'N/A')}")
        if data.get("sma_20"):
            parts.append(f"SMA20: ${data['sma_20']} | SMA50: ${data.get('sma_50', 'N/A')}")
        if data.get("rsi") is not None:
            parts.append(f"RSI(14): {data['rsi']}")
        macd = data.get("macd")
        if macd:
            parts.append(f"MACD: {macd['macd']} | Signal: {macd['signal']} | Hist: {macd['histogram']} | Crossover: {macd['crossover']}")
        bb = data.get("bollinger")
        if bb:
            parts.append(f"Bollinger: [{bb['lower']}, {bb['middle']}, {bb['upper']}] Position: {bb['position']}")
        if data.get("volume_ratio") is not None:
            parts.append(f"Volume Ratio (vs 20d avg): {data['volume_ratio']}x")
        changes = []
        if data.get("change_1d_pct") is not None:
            changes.append(f"1d: {data['change_1d_pct']:+.2f}%")
        if data.get("change_5d_pct") is not None:
            changes.append(f"5d: {data['change_5d_pct']:+.2f}%")
        if data.get("change_20d_pct") is not None:
            changes.append(f"20d: {data['change_20d_pct']:+.2f}%")
        if changes:
            parts.append(f"Changes: {' | '.join(changes)}")

    return "\n".join(parts)


def analyze(
    market_data: dict,
    portfolio: dict,
    holdings: list[dict],
) -> AIAnalysisResult:
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    user_prompt = _build_user_prompt(market_data, portfolio, holdings)

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_text = "\n".join(lines)

    parsed = json.loads(raw_text)
    return AIAnalysisResult.model_validate(parsed)
