import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
CRON_SECRET = os.environ.get("CRON_SECRET", "")

CLAUDE_MODEL = "claude-sonnet-4-5-20241022"

INITIAL_BALANCE = 2000.0

WATCHLIST_ETFS = ["SPY", "QQQ", "IWM", "VTI", "XLF", "XLK", "XLE", "XLV", "GLD", "TLT"]
WATCHLIST_STOCKS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "JNJ", "V"]
WATCHLIST = WATCHLIST_ETFS + WATCHLIST_STOCKS

SECTOR_MAP = {
    "SPY": "Broad Market",
    "QQQ": "Technology",
    "IWM": "Small Cap",
    "VTI": "Broad Market",
    "XLF": "Financials",
    "XLK": "Technology",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "GLD": "Commodities",
    "TLT": "Bonds",
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOGL": "Technology",
    "AMZN": "Consumer Discretionary",
    "NVDA": "Technology",
    "META": "Technology",
    "TSLA": "Consumer Discretionary",
    "JPM": "Financials",
    "JNJ": "Healthcare",
    "V": "Financials",
}

# Risk parameters
MAX_SINGLE_POSITION_PCT = 0.20
MAX_SINGLE_SECTOR_PCT = 0.40
MIN_CASH_RESERVE_PCT = 0.10
CONFIDENCE_THRESHOLD = 0.70
STOP_LOSS_PCT = 0.08
MAX_TRADE_SIZE_PCT = 0.10
