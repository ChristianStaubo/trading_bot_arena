from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import logging

from database import get_db
from .service import trading_service
from .dto import (
    CreateTradeSignalDto, CreateOrderDto, CreateExecutedTradeDto, 
    CreateOrderCancellationDto, UpdateExecutedTradeDto
)
from .responses import (
    TradeSignalResponse, OrderResponse, ExecutedTradeResponse, OrderCancellationResponse,
    TradeSignalSummaryResponse, ExecutedTradeSummaryResponse
)


router = APIRouter(prefix="/trades", tags=["trades"])

# Set up logger for API debugging 
logger = logging.getLogger("api")

# Trade Signals Endpoints
@router.post("/trade-signals", response_model=TradeSignalResponse, status_code=201)
async def create_trade_signal(
    dto: CreateTradeSignalDto,
    db: AsyncSession = Depends(get_db),
):
    """Create a new trade signal"""
    logger.info(f"✅ Trade signal validation passed - creating record")
    result = await trading_service.create_trade_signal(db, dto)
    logger.info(f"✅ Trade signal created successfully: {result.id}")
    return result


@router.get("/trade-signals", response_model=List[TradeSignalSummaryResponse])
async def get_trade_signals(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    bot_name: Optional[str] = Query(None, description="Filter by bot name"),
    strategy_name: Optional[str] = Query(None, description="Filter by strategy name"),
    order_placed: Optional[bool] = Query(None, description="Filter by whether order was placed"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Get trade signals with optional filtering"""
    return await trading_service.get_trade_signals(
        db, symbol=symbol, bot_name=bot_name, strategy_name=strategy_name, 
        order_placed=order_placed, limit=limit
    )


@router.get("/trade-signals/{signal_id}", response_model=TradeSignalResponse)
async def get_trade_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific trade signal by ID"""
    signal = await trading_service.get_trade_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Trade signal not found")
    return signal


# Orders Endpoints
@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    dto: CreateOrderDto,
    db: AsyncSession = Depends(get_db),
):
    """Create a new order record"""
    return await trading_service.create_order(db, dto)


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    bot_name: Optional[str] = Query(None, description="Filter by bot name"),
    success: Optional[bool] = Query(None, description="Filter by order success"),
    parent_order_id: Optional[int] = Query(None, description="Filter by IBKR parent order ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Get orders with optional filtering"""
    return await trading_service.get_orders(
        db, symbol=symbol, bot_name=bot_name, success=success, 
        parent_order_id=parent_order_id, limit=limit
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific order by ID"""
    order = await trading_service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# Executed Trades Endpoints
@router.post("/executed-trades", response_model=ExecutedTradeResponse, status_code=201)
async def create_executed_trade(
    dto: CreateExecutedTradeDto,
    db: AsyncSession = Depends(get_db),
):
    """Create a new executed trade"""
    return await trading_service.create_executed_trade(db, dto)


@router.get("/executed-trades", response_model=List[ExecutedTradeSummaryResponse])
async def get_executed_trades(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    bot_name: Optional[str] = Query(None, description="Filter by bot name"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    ibkr_order_id: Optional[int] = Query(None, description="Filter by IBKR order ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Get executed trades with optional filtering"""
    return await trading_service.get_executed_trades(
        db, symbol=symbol, bot_name=bot_name, status=status, 
        ibkr_order_id=ibkr_order_id, limit=limit
    )


@router.get("/executed-trades/{trade_id}", response_model=ExecutedTradeResponse)
async def get_executed_trade(
    trade_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific executed trade by ID"""
    trade = await trading_service.get_executed_trade_by_id(db, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Executed trade not found")
    return trade


@router.patch("/executed-trades/{trade_id}", response_model=ExecutedTradeResponse)
async def update_executed_trade(
    trade_id: UUID,
    dto: UpdateExecutedTradeDto,
    db: AsyncSession = Depends(get_db),
):
    """Update an executed trade (typically for order status updates)"""
    trade = await trading_service.update_executed_trade(db, trade_id, dto)
    if not trade:
        raise HTTPException(status_code=404, detail="Executed trade not found")
    return trade


@router.get("/executed-trades/ibkr/{ibkr_order_id}", response_model=ExecutedTradeResponse)
async def get_executed_trade_by_ibkr_order_id(
    ibkr_order_id: int,
    bot_name: str = Query(..., description="Bot name to uniquely identify the order"),
    db: AsyncSession = Depends(get_db),
):
    """Get executed trade by IBKR order ID and bot name"""
    trade = await trading_service.get_executed_trade_by_ibkr_order_id(db, ibkr_order_id, bot_name)
    if not trade:
        raise HTTPException(status_code=404, detail="Executed trade not found")
    return trade


# Order Cancellations Endpoints
@router.post("/order-cancellations", response_model=OrderCancellationResponse, status_code=201)
async def create_order_cancellation(
    dto: CreateOrderCancellationDto,
    db: AsyncSession = Depends(get_db),
):
    """Create a new order cancellation record"""
    return await trading_service.create_order_cancellation(db, dto)


@router.get("/order-cancellations", response_model=List[OrderCancellationResponse])
async def get_order_cancellations(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    bot_name: Optional[str] = Query(None, description="Filter by bot name"),
    reason: Optional[str] = Query(None, description="Filter by cancellation reason"),
    ibkr_order_id: Optional[int] = Query(None, description="Filter by IBKR order ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Get order cancellations with optional filtering"""
    return await trading_service.get_order_cancellations(
        db, symbol=symbol, bot_name=bot_name, reason=reason, 
        ibkr_order_id=ibkr_order_id, limit=limit
    )


@router.get("/order-cancellations/{cancellation_id}", response_model=OrderCancellationResponse)
async def get_order_cancellation(
    cancellation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific order cancellation by ID"""
    cancellation = await trading_service.get_order_cancellation_by_id(db, cancellation_id)
    if not cancellation:
        raise HTTPException(status_code=404, detail="Order cancellation not found")
    return cancellation


