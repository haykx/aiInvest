from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from supabase import create_client, Client

import config


def get_client() -> Client:
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


# --- Portfolio ---

def get_portfolio(client: Client) -> dict:
    resp = client.table("portfolio").select("*").eq("id", "main").execute()
    if resp.data:
        return resp.data[0]
    return initialize_portfolio(client)


def initialize_portfolio(client: Client) -> dict:
    row = {
        "id": "main",
        "cash_balance": config.INITIAL_BALANCE,
        "total_value": config.INITIAL_BALANCE,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client.table("portfolio").upsert(row).execute()
    return row


def update_portfolio(client: Client, cash_balance: float, total_value: float) -> None:
    client.table("portfolio").update({
        "cash_balance": cash_balance,
        "total_value": total_value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", "main").execute()


# --- Holdings ---

def get_holdings(client: Client) -> list[dict]:
    resp = client.table("holdings").select("*").execute()
    return resp.data or []


def upsert_holding(client: Client, holding: dict) -> None:
    client.table("holdings").upsert(holding).execute()


def delete_holding(client: Client, ticker: str) -> None:
    client.table("holdings").delete().eq("ticker", ticker).execute()


def update_holding_prices(client: Client, price_map: dict[str, float]) -> None:
    for ticker, price in price_map.items():
        client.table("holdings").update(
            {"current_price": price}
        ).eq("ticker", ticker).execute()


# --- Transactions ---

def log_transaction(client: Client, txn: dict) -> None:
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": txn["action"],
        "ticker": txn["ticker"],
        "shares": txn["shares"],
        "price": txn["price"],
        "total_cost": txn["total_cost"],
        "reasoning": txn.get("reasoning", ""),
        "portfolio_value_after": txn.get("portfolio_value_after", 0),
        "cash_after": txn.get("cash_after", 0),
    }
    client.table("transactions").insert(row).execute()


def get_transactions(client: Client, limit: int = 50, offset: int = 0) -> list[dict]:
    resp = (
        client.table("transactions")
        .select("*")
        .order("timestamp", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return resp.data or []


# --- Analysis Runs ---

def log_analysis_run(client: Client, run_data: dict) -> None:
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_data": run_data.get("market_data"),
        "ai_analysis": run_data.get("ai_analysis"),
        "recommendations": run_data.get("recommendations"),
        "actions_taken": run_data.get("actions_taken"),
        "run_duration": run_data.get("run_duration"),
        "error": run_data.get("error"),
    }
    client.table("analysis_runs").insert(row).execute()


def get_analysis_runs(client: Client, limit: int = 10) -> list[dict]:
    resp = (
        client.table("analysis_runs")
        .select("*")
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


# --- Stop-Loss Events ---

def log_stop_loss_event(client: Client, event: dict) -> None:
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticker": event["ticker"],
        "trigger_price": event["trigger_price"],
        "avg_cost": event["avg_cost"],
        "shares": event["shares"],
        "loss_pct": event["loss_pct"],
    }
    client.table("stop_loss_events").insert(row).execute()
