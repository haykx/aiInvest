# aiInvest — AI-Powered Stock Market Analysis & Trading System

Uses Claude AI to analyze the US stock market twice daily, making mock investment decisions aimed at maximizing profit with low risk. Starts with a virtual $2,000 balance.

## Architecture

- **Runtime**: Vercel Python serverless functions
- **AI**: Claude Sonnet 4.5 via Anthropic API
- **Data**: yfinance (free, no API key)
- **Persistence**: Supabase (PostgreSQL)
- **Schedule**: Twice-daily cron (midnight + noon UTC)

## Prerequisites

- Python 3.12+
- [Supabase](https://supabase.com) account (free tier works)
- [Anthropic](https://console.anthropic.com) API key
- [Vercel](https://vercel.com) account

## Local Development

```bash
# 1. Clone and set up
cd aiInvest
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env .env
# Edit .env with your keys

# 3. Set up database
# Run schema.sql in the Supabase SQL editor

# 4. Run locally with Vercel CLI
npm i -g vercel
vercel dev
```

## Deployment

```bash
# Deploy to Vercel
vercel deploy --prod

# Set environment variables in Vercel dashboard:
# - ANTHROPIC_API_KEY
# - SUPABASE_URL
# - SUPABASE_KEY
# - CRON_SECRET
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | GET/POST | Run analysis + trading pipeline (cron) |
| `/api/status` | GET | Current portfolio snapshot |
| `/api/history` | GET | Transaction history (`?limit=50&offset=0`) |

The `/api/analyze` endpoint requires `Authorization: Bearer <CRON_SECRET>` header.

## Cron Setup

Vercel Hobby plan supports one daily cron (configured in `vercel.json` for midnight UTC). For the second daily trigger (noon UTC), use an external cron service like [cron-job.org](https://cron-job.org) to hit `/api/analyze` with the authorization header.

Vercel Pro plan ($20/mo) supports multiple crons natively.

## Risk Management

- Max 20% of portfolio in any single position
- Max 40% in any single sector
- Minimum 10% cash reserve maintained
- 8% automatic stop-loss on all positions
- Confidence threshold of 0.70 for new buys
- Max 10% of portfolio per trade

## Watchlist

**ETFs**: SPY, QQQ, IWM, VTI, XLF, XLK, XLE, XLV, GLD, TLT
**Stocks**: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, JNJ, V

## Cost Estimate

~$1-2/month for Anthropic API (Claude Sonnet, ~3K input + ~1.5K output tokens × 2 runs/day).
