from __future__ import annotations

import pandas as pd
import yfinance as yf


def calculate_rsi(series: pd.Series, period: int = 14) -> float | None:
    if len(series) < period + 1:
        return None
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.iloc[1 : period + 1].mean()
    avg_loss = loss.iloc[1 : period + 1].mean()
    for i in range(period + 1, len(gain)):
        avg_gain = (avg_gain * (period - 1) + gain.iloc[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss.iloc[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calculate_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> dict | None:
    if len(series) < slow + signal:
        return None
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    crossover = "BULLISH" if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0 else (
        "BEARISH" if histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0 else "NONE"
    )
    return {
        "macd": round(float(macd_line.iloc[-1]), 4),
        "signal": round(float(signal_line.iloc[-1]), 4),
        "histogram": round(float(histogram.iloc[-1]), 4),
        "crossover": crossover,
    }


def calculate_bollinger_bands(
    series: pd.Series, period: int = 20, std: int = 2
) -> dict | None:
    if len(series) < period:
        return None
    sma = series.rolling(window=period).mean()
    rolling_std = series.rolling(window=period).std()
    upper = sma + (rolling_std * std)
    lower = sma - (rolling_std * std)
    current_price = float(series.iloc[-1])
    band_width = float(upper.iloc[-1]) - float(lower.iloc[-1])
    position = (current_price - float(lower.iloc[-1])) / band_width if band_width > 0 else 0.5
    return {
        "upper": round(float(upper.iloc[-1]), 2),
        "middle": round(float(sma.iloc[-1]), 2),
        "lower": round(float(lower.iloc[-1]), 2),
        "position": round(position, 4),
    }


def _build_ticker_indicators(close: pd.Series, volume: pd.Series) -> dict:
    current_price = round(float(close.iloc[-1]), 2)

    sma_20 = round(float(close.rolling(20).mean().iloc[-1]), 2) if len(close) >= 20 else None
    sma_50 = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else None

    vol_avg_20 = float(volume.rolling(20).mean().iloc[-1]) if len(volume) >= 20 else None
    volume_ratio = round(float(volume.iloc[-1]) / vol_avg_20, 2) if vol_avg_20 and vol_avg_20 > 0 else None

    pct_1d = round(float((close.iloc[-1] / close.iloc[-2] - 1) * 100), 2) if len(close) >= 2 else None
    pct_5d = round(float((close.iloc[-1] / close.iloc[-6] - 1) * 100), 2) if len(close) >= 6 else None
    pct_20d = round(float((close.iloc[-1] / close.iloc[-21] - 1) * 100), 2) if len(close) >= 21 else None

    return {
        "price": current_price,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "rsi": calculate_rsi(close),
        "macd": calculate_macd(close),
        "bollinger": calculate_bollinger_bands(close),
        "volume_ratio": volume_ratio,
        "change_1d_pct": pct_1d,
        "change_5d_pct": pct_5d,
        "change_20d_pct": pct_20d,
    }


def fetch_market_data(tickers: list[str], period: str = "90d") -> dict[str, dict]:
    results = {}
    try:
        data = yf.download(tickers, period=period, threads=True, progress=False)
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    close = data["Close"].dropna()
                    volume = data["Volume"].dropna()
                else:
                    close = data["Close"][ticker].dropna()
                    volume = data["Volume"][ticker].dropna()
                if len(close) < 2:
                    continue
                results[ticker] = _build_ticker_indicators(close, volume)
            except (KeyError, IndexError):
                continue
    except Exception:
        # Fallback: individual downloads
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period=period)
                if len(hist) < 2:
                    continue
                results[ticker] = _build_ticker_indicators(hist["Close"], hist["Volume"])
            except Exception:
                continue
    return results


def get_market_context() -> dict:
    context = {}
    try:
        spy = yf.Ticker("SPY")
        spy_hist = spy.history(period="5d")
        if len(spy_hist) >= 2:
            spy_price = float(spy_hist["Close"].iloc[-1])
            spy_change = (spy_hist["Close"].iloc[-1] / spy_hist["Close"].iloc[-2] - 1) * 100
            context["spy"] = {
                "price": round(spy_price, 2),
                "change_1d_pct": round(float(spy_change), 2),
            }
    except Exception:
        pass
    try:
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        if len(vix_hist) >= 1:
            context["vix"] = round(float(vix_hist["Close"].iloc[-1]), 2)
    except Exception:
        pass
    return context


def build_analysis_payload(tickers: list[str]) -> dict:
    market_context = get_market_context()
    ticker_data = fetch_market_data(tickers)
    return {
        "market_context": market_context,
        "tickers": ticker_data,
    }
