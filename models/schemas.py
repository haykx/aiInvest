from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class StockRecommendation(BaseModel):
    ticker: str
    action: Action
    confidence: float = Field(ge=0.0, le=1.0)
    allocation_pct: float = Field(ge=0.0, le=100.0)
    risk_level: RiskLevel
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    reasoning: str


class MarketOverview(BaseModel):
    overall_sentiment: str
    vix_assessment: str
    key_factors: list[str]
    sector_outlook: dict[str, str]


class AIAnalysisResult(BaseModel):
    market_overview: MarketOverview
    recommendations: list[StockRecommendation]
    portfolio_commentary: str
    risk_warnings: list[str]


class Holding(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    current_price: float
    sector: str
    purchased_at: Optional[str] = None

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_cost) * self.shares

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        return (self.current_price - self.avg_cost) / self.avg_cost * 100


class Transaction(BaseModel):
    timestamp: Optional[str] = None
    action: Action
    ticker: str
    shares: float
    price: float
    total_cost: float
    reasoning: str
    portfolio_value_after: float
    cash_after: float


class PortfolioState(BaseModel):
    cash_balance: float
    total_value: float
    holdings: list[Holding] = []
    updated_at: Optional[str] = None
