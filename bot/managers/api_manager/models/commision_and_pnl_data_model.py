from typing import Optional
from pydantic import BaseModel, Field


class CommissionAndPnlData(BaseModel):
    """Type-safe model for commission and P&L data extracted from trade fills"""
    commission: Optional[float] = Field(None, description="Total commission from all fills")
    realized_pnl: Optional[float] = Field(None, description="Total realized P&L from all fills")
