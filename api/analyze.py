from http.server import BaseHTTPRequestHandler
import json
import time
import traceback

import config
from core import database, market_data, ai_analyzer, risk_manager, portfolio_manager


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        return self._run()

    def do_POST(self):
        return self._run()

    def _run(self):
        start = time.time()

        # Verify cron secret
        auth = self.headers.get("Authorization", "")
        if config.CRON_SECRET and auth != f"Bearer {config.CRON_SECRET}":
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
            return

        client = database.get_client()
        error_msg = None
        analysis_result = None
        actions_taken = []
        market = None

        try:
            # 1. Load portfolio state
            portfolio = database.get_portfolio(client)
            holdings = database.get_holdings(client)

            # 2. Fetch market data
            market = market_data.build_analysis_payload(config.WATCHLIST)

            # 3. Update holding prices with latest data
            price_map = {}
            for ticker, data in market.get("tickers", {}).items():
                if "price" in data:
                    price_map[ticker] = data["price"]
            if price_map:
                database.update_holding_prices(client, {
                    t: p for t, p in price_map.items()
                    if any(h["ticker"] == t for h in holdings)
                })
                # Refresh holdings after price update
                holdings = database.get_holdings(client)

            # 4. AI analysis
            analysis_result = ai_analyzer.analyze(market, portfolio, holdings)

            # 5. Risk filter
            approved = risk_manager.filter_recommendations(
                analysis_result, holdings, portfolio, price_map
            )

            # 6. Log stop-loss events
            stop_losses = risk_manager.check_stop_losses(holdings, price_map)
            for sl in stop_losses:
                database.log_stop_loss_event(client, sl)

            # 7. Execute trades
            if approved:
                actions_taken = portfolio_manager.execute_trades(
                    client, approved, portfolio, holdings
                )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

        # 8. Log analysis run
        duration = round(time.time() - start, 2)
        try:
            database.log_analysis_run(client, {
                "market_data": market.get("market_context") if market else None,
                "ai_analysis": analysis_result.model_dump_json() if analysis_result else None,
                "recommendations": [
                    r.model_dump() for r in analysis_result.recommendations
                ] if analysis_result else None,
                "actions_taken": actions_taken,
                "run_duration": duration,
                "error": error_msg,
            })
        except Exception:
            pass  # Don't fail the response if logging fails

        # Response
        status = 200 if not error_msg else 500
        body = {
            "status": "ok" if not error_msg else "error",
            "duration_seconds": duration,
            "trades_executed": len(actions_taken),
            "actions": actions_taken,
        }
        if error_msg:
            body["error"] = error_msg

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, default=str).encode())
