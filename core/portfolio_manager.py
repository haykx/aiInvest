from __future__ import annotations

from supabase import Client

import config
from core import database


def execute_trades(
    client: Client,
    approved_trades: list[dict],
    portfolio: dict,
    holdings: list[dict],
) -> list[dict]:
    """Execute mock trades, updating DB. Returns list of executed trades."""
    cash = portfolio["cash_balance"]
    executed = []
    holdings_map = {h["ticker"]: dict(h) for h in holdings}

    for trade in approved_trades:
        try:
            ticker = trade["ticker"]
            action = trade["action"]
            shares = trade["shares"]
            price = trade["price"]
            total_cost = trade["total_cost"]

            if action == "SELL":
                if ticker not in holdings_map:
                    continue
                holding = holdings_map[ticker]
                sell_shares = min(shares, holding["shares"])
                proceeds = round(sell_shares * price, 2)
                cash += proceeds

                remaining = round(holding["shares"] - sell_shares, 4)
                if remaining <= 0.0001:
                    database.delete_holding(client, ticker)
                    del holdings_map[ticker]
                else:
                    holdings_map[ticker]["shares"] = remaining
                    database.upsert_holding(client, {
                        "ticker": ticker,
                        "shares": remaining,
                        "avg_cost": holding["avg_cost"],
                        "current_price": price,
                        "sector": holding.get("sector", config.SECTOR_MAP.get(ticker, "Unknown")),
                    })

            elif action == "BUY":
                if total_cost > cash:
                    continue
                cash -= total_cost
                cash = round(cash, 2)

                if ticker in holdings_map:
                    existing = holdings_map[ticker]
                    old_total = existing["shares"] * existing["avg_cost"]
                    new_total = shares * price
                    combined_shares = round(existing["shares"] + shares, 4)
                    new_avg_cost = round((old_total + new_total) / combined_shares, 2)
                    holdings_map[ticker] = {
                        "ticker": ticker,
                        "shares": combined_shares,
                        "avg_cost": new_avg_cost,
                        "current_price": price,
                        "sector": existing.get("sector", config.SECTOR_MAP.get(ticker, "Unknown")),
                    }
                else:
                    holdings_map[ticker] = {
                        "ticker": ticker,
                        "shares": shares,
                        "avg_cost": price,
                        "current_price": price,
                        "sector": config.SECTOR_MAP.get(ticker, "Unknown"),
                    }
                database.upsert_holding(client, holdings_map[ticker])

            # Calculate portfolio value after this trade
            holdings_value = sum(
                h["shares"] * h.get("current_price", h["avg_cost"])
                for h in holdings_map.values()
            )
            total_value = round(cash + holdings_value, 2)

            database.log_transaction(client, {
                "action": action,
                "ticker": ticker,
                "shares": shares if action == "BUY" else sell_shares,
                "price": price,
                "total_cost": total_cost if action == "BUY" else proceeds,
                "reasoning": trade.get("reasoning", ""),
                "portfolio_value_after": total_value,
                "cash_after": cash,
            })

            executed.append({
                "ticker": ticker,
                "action": action,
                "shares": shares if action == "BUY" else sell_shares,
                "price": price,
            })

        except Exception as e:
            # Partial execution: log error but continue
            print(f"Trade execution error for {trade.get('ticker')}: {e}")
            continue

    # Update portfolio totals
    holdings_value = sum(
        h["shares"] * h.get("current_price", h["avg_cost"])
        for h in holdings_map.values()
    )
    total_value = round(cash + holdings_value, 2)
    database.update_portfolio(client, cash, total_value)

    return executed


def calculate_portfolio_value(cash: float, holdings: list[dict]) -> float:
    holdings_value = sum(
        h["shares"] * h.get("current_price", h["avg_cost"])
        for h in holdings
    )
    return round(cash + holdings_value, 2)


def get_portfolio_snapshot(client: Client) -> dict:
    """Full portfolio state for the status API."""
    portfolio = database.get_portfolio(client)
    holdings = database.get_holdings(client)

    holdings_detail = []
    sector_allocation: dict[str, float] = {}
    total_holdings_value = 0

    for h in holdings:
        value = h["shares"] * h.get("current_price", h["avg_cost"])
        total_holdings_value += value
        sector = h.get("sector", "Unknown")
        sector_allocation[sector] = sector_allocation.get(sector, 0) + value
        pnl = (h.get("current_price", h["avg_cost"]) - h["avg_cost"]) * h["shares"]
        pnl_pct = ((h.get("current_price", h["avg_cost"]) / h["avg_cost"]) - 1) * 100 if h["avg_cost"] > 0 else 0
        holdings_detail.append({
            "ticker": h["ticker"],
            "shares": h["shares"],
            "avg_cost": h["avg_cost"],
            "current_price": h.get("current_price", h["avg_cost"]),
            "sector": sector,
            "market_value": round(value, 2),
            "unrealized_pnl": round(pnl, 2),
            "unrealized_pnl_pct": round(pnl_pct, 2),
        })

    total_value = portfolio["cash_balance"] + total_holdings_value
    initial = config.INITIAL_BALANCE
    total_return = round((total_value / initial - 1) * 100, 2) if initial > 0 else 0

    # Normalize sector allocation to percentages
    sector_pcts = {}
    if total_value > 0:
        sector_pcts = {s: round(v / total_value * 100, 2) for s, v in sector_allocation.items()}
        sector_pcts["Cash"] = round(portfolio["cash_balance"] / total_value * 100, 2)

    return {
        "cash_balance": round(portfolio["cash_balance"], 2),
        "total_value": round(total_value, 2),
        "total_return_pct": total_return,
        "holdings": holdings_detail,
        "sector_allocation": sector_pcts,
        "updated_at": portfolio.get("updated_at"),
    }
