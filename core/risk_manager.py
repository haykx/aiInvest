from __future__ import annotations

import config
from models.schemas import AIAnalysisResult, Action


def check_stop_losses(holdings: list[dict], price_map: dict[str, float]) -> list[dict]:
    """Return holdings that triggered the 8% stop-loss."""
    triggered = []
    for h in holdings:
        ticker = h["ticker"]
        current_price = price_map.get(ticker, h.get("current_price", 0))
        avg_cost = h["avg_cost"]
        if avg_cost <= 0:
            continue
        loss_pct = (avg_cost - current_price) / avg_cost
        if loss_pct >= config.STOP_LOSS_PCT:
            triggered.append({
                "ticker": ticker,
                "trigger_price": current_price,
                "avg_cost": avg_cost,
                "shares": h["shares"],
                "loss_pct": round(loss_pct * 100, 2),
            })
    return triggered


def calculate_max_investable(cash: float, total_value: float) -> float:
    """Cash minus the minimum 10% reserve."""
    reserve = total_value * config.MIN_CASH_RESERVE_PCT
    return max(0, cash - reserve)


def _get_sector_exposure(holdings: list[dict], total_value: float) -> dict[str, float]:
    """Current sector exposure as fraction of portfolio."""
    exposure: dict[str, float] = {}
    for h in holdings:
        sector = h.get("sector", "Unknown")
        value = h["shares"] * h.get("current_price", h["avg_cost"])
        exposure[sector] = exposure.get(sector, 0) + value
    return {s: v / total_value for s, v in exposure.items()} if total_value > 0 else exposure


def _get_position_pct(ticker: str, holdings: list[dict], total_value: float) -> float:
    """Current position size as fraction of portfolio."""
    for h in holdings:
        if h["ticker"] == ticker:
            value = h["shares"] * h.get("current_price", h["avg_cost"])
            return value / total_value if total_value > 0 else 0
    return 0.0


def calculate_position_size(
    ticker: str,
    price: float,
    allocation_pct: float,
    cash: float,
    total_value: float,
    holdings: list[dict],
) -> tuple[float, float]:
    """Return (shares, total_cost) respecting all limits."""
    if price <= 0 or total_value <= 0:
        return 0, 0

    sector = config.SECTOR_MAP.get(ticker, "Unknown")
    sector_exposure = _get_sector_exposure(holdings, total_value)
    position_pct = _get_position_pct(ticker, holdings, total_value)

    # Cap by single position limit
    max_position_room = config.MAX_SINGLE_POSITION_PCT - position_pct
    # Cap by sector limit
    current_sector = sector_exposure.get(sector, 0)
    max_sector_room = config.MAX_SINGLE_SECTOR_PCT - current_sector
    # Cap by max trade size
    max_trade = config.MAX_TRADE_SIZE_PCT
    # Cap by cash available (minus reserve)
    max_investable = calculate_max_investable(cash, total_value)

    # Effective allocation is the minimum of all constraints
    effective_pct = min(
        allocation_pct / 100,
        max_position_room,
        max_sector_room,
        max_trade,
    )
    effective_pct = max(0, effective_pct)

    desired_amount = total_value * effective_pct
    actual_amount = min(desired_amount, max_investable)

    if actual_amount < price * 0.01:  # Skip tiny trades
        return 0, 0

    shares = actual_amount / price
    # Round to 4 decimal places (fractional shares)
    shares = round(shares, 4)
    total_cost = round(shares * price, 2)

    return shares, total_cost


def filter_recommendations(
    analysis: AIAnalysisResult,
    holdings: list[dict],
    portfolio: dict,
    price_map: dict[str, float],
) -> list[dict]:
    """Apply all risk rules and return approved trades."""
    cash = portfolio.get("cash_balance", 0)
    total_value = portfolio.get("total_value", 0)
    approved = []

    # 1. Check stop-losses — forced SELLs
    stop_loss_hits = check_stop_losses(holdings, price_map)
    for sl in stop_loss_hits:
        approved.append({
            "ticker": sl["ticker"],
            "action": "SELL",
            "shares": sl["shares"],
            "price": sl["trigger_price"],
            "total_cost": round(sl["shares"] * sl["trigger_price"], 2),
            "reasoning": f"Stop-loss triggered: {sl['loss_pct']}% loss (threshold: {config.STOP_LOSS_PCT * 100}%)",
            "is_stop_loss": True,
        })
    stop_loss_tickers = {sl["ticker"] for sl in stop_loss_hits}

    # 2. Filter by confidence and sort: SELLs first, then BUYs by confidence desc
    sells = []
    buys = []
    for rec in analysis.recommendations:
        if rec.ticker in stop_loss_tickers:
            continue  # Already handled by stop-loss
        if rec.action == Action.HOLD:
            continue
        if rec.action == Action.SELL:
            # Find holding to sell
            holding = next((h for h in holdings if h["ticker"] == rec.ticker), None)
            if holding:
                sells.append((rec, holding))
        elif rec.action == Action.BUY and rec.confidence >= config.CONFIDENCE_THRESHOLD:
            buys.append(rec)

    # Process SELLs
    for rec, holding in sells:
        price = price_map.get(rec.ticker, holding.get("current_price", 0))
        shares = holding["shares"]
        approved.append({
            "ticker": rec.ticker,
            "action": "SELL",
            "shares": shares,
            "price": price,
            "total_cost": round(shares * price, 2),
            "reasoning": rec.reasoning,
            "is_stop_loss": False,
        })
        # Update cash for subsequent BUY calculations
        cash += shares * price

    # Process BUYs sorted by confidence descending
    buys.sort(key=lambda r: r.confidence, reverse=True)
    for rec in buys:
        price = price_map.get(rec.ticker, 0)
        if price <= 0:
            continue
        shares, total_cost = calculate_position_size(
            rec.ticker, price, rec.allocation_pct, cash, total_value, holdings
        )
        if shares <= 0:
            continue
        approved.append({
            "ticker": rec.ticker,
            "action": "BUY",
            "shares": shares,
            "price": price,
            "total_cost": total_cost,
            "reasoning": rec.reasoning,
            "is_stop_loss": False,
        })
        cash -= total_cost

    return approved
