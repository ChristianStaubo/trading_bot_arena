from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from uuid import UUID
from datetime import datetime

from database.models import TradeSignal, Order, ExecutedTrade, OrderCancellation
from ..dto import (
    CreateTradeSignalDto, CreateOrderDto, CreateExecutedTradeDto, 
    CreateOrderCancellationDto, UpdateExecutedTradeDto
)
from ..responses import (
    TradeSignalResponse, OrderResponse, ExecutedTradeResponse, OrderCancellationResponse,
    TradeSignalSummaryResponse, ExecutedTradeSummaryResponse
)


class TradingService:
    """Service class for trading operations"""

    # =================== TRADE SIGNALS ===================
    
    async def create_trade_signal(
        self, db: AsyncSession, dto: CreateTradeSignalDto
    ) -> TradeSignalResponse:
        """Create a new trade signal"""
        trade_signal = TradeSignal(
            bot_name=dto.bot_name,
            symbol=dto.symbol,
            strategy_name=dto.strategy_name,
            timeframe=dto.timeframe,
            action=dto.action,
            entry_price=dto.entry_price,
            stop_loss=dto.stop_loss,
            take_profit=dto.take_profit,
            confidence=dto.confidence,
            reason=dto.reason,
            max_concurrent_trades=dto.max_concurrent_trades,
            current_active_trades=dto.current_active_trades,
            order_placed=dto.order_placed
        )
        
        db.add(trade_signal)
        await db.commit()
        await db.refresh(trade_signal)
        
        return TradeSignalResponse.model_validate(trade_signal)

    async def get_trade_signals(
        self, 
        db: AsyncSession, 
        symbol: Optional[str] = None,
        bot_name: Optional[str] = None,
        strategy_name: Optional[str] = None,
        order_placed: Optional[bool] = None,
        limit: int = 100
    ) -> List[TradeSignalSummaryResponse]:
        """Get trade signals with optional filtering"""
        query = select(TradeSignal).order_by(desc(TradeSignal.timestamp))
        
        if symbol:
            query = query.filter(TradeSignal.symbol == symbol)
        if bot_name:
            query = query.filter(TradeSignal.bot_name == bot_name)
        if strategy_name:
            query = query.filter(TradeSignal.strategy_name == strategy_name)
        if order_placed is not None:
            query = query.filter(TradeSignal.order_placed == order_placed)
            
        query = query.limit(limit)
        
        result = await db.execute(query)
        signals = result.scalars().all()
        
        return [TradeSignalSummaryResponse.model_validate(signal) for signal in signals]

    async def get_trade_signal_by_id(
        self, db: AsyncSession, signal_id: UUID
    ) -> Optional[TradeSignalResponse]:
        """Get a specific trade signal by ID"""
        result = await db.execute(
            select(TradeSignal).filter(TradeSignal.id == signal_id)
        )
        signal = result.scalars().first()
        
        if signal:
            return TradeSignalResponse.model_validate(signal)
        return None

    # =================== ORDERS ===================
    
    async def create_order(
        self, db: AsyncSession, dto: CreateOrderDto
    ) -> OrderResponse:
        """Create a new order record"""
        order = Order(
            trade_signal_id=dto.trade_signal_id,
            bot_name=dto.bot_name,
            symbol=dto.symbol,
            success=dto.success,
            error=dto.error,
            parent_order_id=dto.parent_order_id,
            order_type=dto.order_type,
            quantity=dto.quantity,
            price=dto.price,
            stop_loss=dto.stop_loss,
            take_profit=dto.take_profit,
            trade_count=dto.trade_count
        )
        
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        return OrderResponse.model_validate(order)

    async def get_orders(
        self,
        db: AsyncSession,
        symbol: Optional[str] = None,
        bot_name: Optional[str] = None,
        success: Optional[bool] = None,
        parent_order_id: Optional[int] = None,
        limit: int = 100
    ) -> List[OrderResponse]:
        """Get orders with optional filtering"""
        query = select(Order).order_by(desc(Order.timestamp))
        
        if symbol:
            query = query.filter(Order.symbol == symbol)
        if bot_name:
            query = query.filter(Order.bot_name == bot_name)
        if success is not None:
            query = query.filter(Order.success == success)
        if parent_order_id is not None:
            query = query.filter(Order.parent_order_id == parent_order_id)
            
        query = query.limit(limit)
        
        result = await db.execute(query)
        orders = result.scalars().all()
        
        return [OrderResponse.model_validate(order) for order in orders]

    async def get_order_by_id(
        self, db: AsyncSession, order_id: UUID
    ) -> Optional[OrderResponse]:
        """Get a specific order by ID"""
        result = await db.execute(
            select(Order).filter(Order.id == order_id)
        )
        order = result.scalars().first()
        
        if order:
            return OrderResponse.model_validate(order)
        return None

    # =================== EXECUTED TRADES ===================
    
    async def create_executed_trade(
        self, db: AsyncSession, dto: CreateExecutedTradeDto
    ) -> ExecutedTradeResponse:
        """Create a new executed trade"""
        executed_trade = ExecutedTrade(
            order_id_ref=dto.order_id_ref,
            bot_name=dto.bot_name,
            symbol=dto.symbol,
            ibkr_order_id=dto.ibkr_order_id,
            ibkr_contract_id=dto.ibkr_contract_id,
            action=dto.action,
            order_type=dto.order_type,
            total_quantity=dto.total_quantity,
            limit_price=dto.limit_price,
            aux_price=dto.aux_price,
            status=dto.status,
            filled_quantity=dto.filled_quantity,
            remaining_quantity=dto.remaining_quantity,
            avg_fill_price=dto.avg_fill_price,
            last_fill_price=dto.last_fill_price,
            commission=dto.commission,
            realized_pnl=dto.realized_pnl,
            unrealized_pnl=dto.unrealized_pnl,
            order_time=dto.order_time,
            account=dto.account,
            exchange=dto.exchange,
            currency=dto.currency
        )
        
        db.add(executed_trade)
        await db.commit()
        await db.refresh(executed_trade)
        
        return ExecutedTradeResponse.model_validate(executed_trade)

    async def update_executed_trade(
        self, db: AsyncSession, trade_id: UUID, dto: UpdateExecutedTradeDto
    ) -> Optional[ExecutedTradeResponse]:
        """Update an executed trade"""
        result = await db.execute(
            select(ExecutedTrade).filter(ExecutedTrade.id == trade_id)
        )
        trade = result.scalars().first()
        
        if not trade:
            return None
        
        # Update only provided fields
        update_data = dto.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(trade, field):
                setattr(trade, field, value)
        
        # Always update the last_update_time
        trade.last_update_time = datetime.utcnow()
        
        await db.commit()
        await db.refresh(trade)
        
        return ExecutedTradeResponse.model_validate(trade)

    async def get_executed_trades(
        self,
        db: AsyncSession,
        symbol: Optional[str] = None,
        bot_name: Optional[str] = None,
        status: Optional[str] = None,
        ibkr_order_id: Optional[int] = None,
        limit: int = 100
    ) -> List[ExecutedTradeSummaryResponse]:
        """Get executed trades with optional filtering"""
        query = select(ExecutedTrade).order_by(desc(ExecutedTrade.fill_time))
        
        if symbol:
            query = query.filter(ExecutedTrade.symbol == symbol)
        if bot_name:
            query = query.filter(ExecutedTrade.bot_name == bot_name)
        if status:
            query = query.filter(ExecutedTrade.status == status)
        if ibkr_order_id is not None:
            query = query.filter(ExecutedTrade.ibkr_order_id == ibkr_order_id)
            
        query = query.limit(limit)
        
        result = await db.execute(query)
        trades = result.scalars().all()
        
        return [ExecutedTradeSummaryResponse.model_validate(trade) for trade in trades]

    async def get_executed_trade_by_id(
        self, db: AsyncSession, trade_id: UUID
    ) -> Optional[ExecutedTradeResponse]:
        """Get a specific executed trade by ID"""
        result = await db.execute(
            select(ExecutedTrade).filter(ExecutedTrade.id == trade_id)
        )
        trade = result.scalars().first()
        
        if trade:
            return ExecutedTradeResponse.model_validate(trade)
        return None

    async def get_executed_trade_by_ibkr_order_id(
        self, db: AsyncSession, ibkr_order_id: int, bot_name: str
    ) -> Optional[ExecutedTradeResponse]:
        """Get executed trade by IBKR order ID and bot name"""
        result = await db.execute(
            select(ExecutedTrade).filter(
                and_(
                    ExecutedTrade.ibkr_order_id == ibkr_order_id,
                    ExecutedTrade.bot_name == bot_name
                )
            )
        )
        trade = result.scalars().first()
        
        if trade:
            return ExecutedTradeResponse.model_validate(trade)
        return None

    # =================== ORDER CANCELLATIONS ===================
    
    async def create_order_cancellation(
        self, db: AsyncSession, dto: CreateOrderCancellationDto
    ) -> OrderCancellationResponse:
        """Create a new order cancellation record"""
        cancellation = OrderCancellation(
            bot_name=dto.bot_name,
            symbol=dto.symbol,
            ibkr_order_id=dto.ibkr_order_id,
            reason=dto.reason
        )
        
        db.add(cancellation)
        await db.commit()
        await db.refresh(cancellation)
        
        return OrderCancellationResponse.model_validate(cancellation)

    async def get_order_cancellations(
        self,
        db: AsyncSession,
        symbol: Optional[str] = None,
        bot_name: Optional[str] = None,
        reason: Optional[str] = None,
        ibkr_order_id: Optional[int] = None,
        limit: int = 100
    ) -> List[OrderCancellationResponse]:
        """Get order cancellations with optional filtering"""
        query = select(OrderCancellation).order_by(desc(OrderCancellation.cancelled_time))
        
        if symbol:
            query = query.filter(OrderCancellation.symbol == symbol)
        if bot_name:
            query = query.filter(OrderCancellation.bot_name == bot_name)
        if reason:
            query = query.filter(OrderCancellation.reason == reason)
        if ibkr_order_id is not None:
            query = query.filter(OrderCancellation.ibkr_order_id == ibkr_order_id)
            
        query = query.limit(limit)
        
        result = await db.execute(query)
        cancellations = result.scalars().all()
        
        return [OrderCancellationResponse.model_validate(cancellation) for cancellation in cancellations]

    async def get_order_cancellation_by_id(
        self, db: AsyncSession, cancellation_id: UUID
    ) -> Optional[OrderCancellationResponse]:
        """Get a specific order cancellation by ID"""
        result = await db.execute(
            select(OrderCancellation).filter(OrderCancellation.id == cancellation_id)
        )
        cancellation = result.scalars().first()
        
        if cancellation:
            return OrderCancellationResponse.model_validate(cancellation)
        return None


# Create service instance
trading_service = TradingService() 