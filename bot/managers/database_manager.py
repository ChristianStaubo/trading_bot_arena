# """
# Database Manager

# Handles all database operations for trade signals, executions, and performance tracking.
# Clean interface for existing bot managers to log data.
# """

# import json
# from datetime import datetime, date, timedelta
# from typing import Dict, Any, Optional, List
# from sqlalchemy import create_engine, func
# from sqlalchemy.orm import sessionmaker, Session
# from database.schema import Base, TradeSignal, Order, Execution, Position, PerformanceStats, SystemEvent


# class DatabaseManager:
#     """Handles all database operations for the trading bot"""
    
#     def __init__(self, database_url: str = "sqlite:///trading_bot.db"):
#         """
#         Initialize database connection
        
#         Args:
#             database_url: SQLite for dev, PostgreSQL for production
#                          Examples: 
#                          - "sqlite:///bot.db" 
#                          - "postgresql://user:pass@localhost/trading_bot"
#         """
#         self.engine = create_engine(database_url)
#         self.SessionLocal = sessionmaker(bind=self.engine)
        
#         # Create tables if they don't exist
#         Base.metadata.create_all(bind=self.engine)
    
#     def get_session(self) -> Session:
#         """Get database session"""
#         return self.SessionLocal()
    
#     # ===================
#     # TRADE SIGNALS
#     # ===================
    
#     def log_trade_signal(self, signal_data: Dict[str, Any]) -> int:
#         """
#         Log a trade signal from strategy
        
#         Args:
#             signal_data: Dict with signal details from TradeDecisionManager
            
#         Returns:
#             Signal ID for linking to orders
#         """
#         with self.get_session() as session:
#             signal = TradeSignal(
#                 symbol=signal_data['symbol'],
#                 strategy_name=signal_data['strategy_name'],
#                 action=signal_data['action'],
#                 entry_price=signal_data['entry_price'],
#                 take_profit=signal_data.get('take_profit'),
#                 stop_loss=signal_data.get('stop_loss'),
#                 confidence=signal_data.get('confidence', 'medium'),
#                 indicators=json.dumps(signal_data.get('indicators', {}))
#             )
#             session.add(signal)
#             session.commit()
#             return signal.id
    
#     # ===================
#     # ORDERS & EXECUTIONS  
#     # ===================
    
#     def log_order(self, order_data: Dict[str, Any], signal_id: Optional[int] = None) -> int:
#         """Log order sent to broker"""
#         with self.get_session() as session:
#             order = Order(
#                 symbol=order_data['symbol'],
#                 broker_order_id=order_data.get('broker_order_id'),
#                 action=order_data['action'],
#                 quantity=order_data['quantity'],
#                 order_type=order_data['order_type'],
#                 limit_price=order_data.get('limit_price'),
#                 stop_price=order_data.get('stop_price'),
#                 status=order_data.get('status', 'SUBMITTED')
#             )
#             session.add(order)
#             session.commit()
            
#             # Link to signal if provided
#             if signal_id:
#                 signal = session.get(TradeSignal, signal_id)
#                 if signal:
#                     signal.order_id = order.id
#                     session.commit()
            
#             return order.id
    
#     def update_order_status(self, broker_order_id: int, status: str, 
#                            filled_qty: int = 0, avg_fill_price: float = None):
#         """Update order status from broker"""
#         with self.get_session() as session:
#             order = session.query(Order).filter_by(broker_order_id=broker_order_id).first()
#             if order:
#                 order.status = status
#                 order.filled_quantity = filled_qty
#                 order.avg_fill_price = avg_fill_price
#                 session.commit()
    
#     def log_execution(self, execution_data: Dict[str, Any]) -> int:
#         """Log trade execution/fill"""
#         with self.get_session() as session:
#             execution = Execution(
#                 symbol=execution_data['symbol'],
#                 order_id=execution_data.get('order_id'),
#                 broker_execution_id=execution_data.get('broker_execution_id'),
#                 action=execution_data['action'],
#                 quantity=execution_data['quantity'],
#                 price=execution_data['price'],
#                 commission=execution_data.get('commission', 0.0)
#             )
#             session.add(execution)
#             session.commit()
#             return execution.id
    
#     # ===================
#     # POSITIONS
#     # ===================
    
#     def update_position(self, position_data: Dict[str, Any]):
#         """Update current position for symbol"""
#         with self.get_session() as session:
#             position = session.query(Position).filter_by(symbol=position_data['symbol']).first()
            
#             if position:
#                 # Update existing position
#                 position.quantity = position_data['quantity']
#                 position.avg_price = position_data['avg_price']
#                 position.current_price = position_data['current_price']
#                 position.unrealized_pnl = position_data.get('unrealized_pnl', 0.0)
#                 position.timestamp = datetime.utcnow()
#             else:
#                 # Create new position
#                 position = Position(
#                     symbol=position_data['symbol'],
#                     quantity=position_data['quantity'],
#                     avg_price=position_data['avg_price'],
#                     current_price=position_data['current_price'],
#                     unrealized_pnl=position_data.get('unrealized_pnl', 0.0),
#                     entry_timestamp=position_data.get('entry_timestamp', datetime.utcnow()),
#                     entry_strategy=position_data.get('entry_strategy')
#                 )
#                 session.add(position)
            
#             session.commit()
    
#     # ===================
#     # PERFORMANCE STATS
#     # ===================
    
#     def calculate_daily_stats(self, symbol: str, target_date: date = None) -> Dict[str, Any]:
#         """Calculate daily performance statistics"""
#         if target_date is None:
#             target_date = date.today()
        
#         with self.get_session() as session:
#             # Get all executions for the day
#             executions = session.query(Execution).filter(
#                 Execution.symbol == symbol,
#                 func.date(Execution.timestamp) == target_date
#             ).all()
            
#             if not executions:
#                 return {}
            
#             # Calculate basic stats
#             total_trades = len(executions)
#             total_commission = sum(e.commission for e in executions)
            
#             # Group by pairs (buy/sell) to calculate P&L
#             # This is simplified - real implementation would be more complex
#             total_pnl = 0.0  # Placeholder
#             winning_trades = 0
#             losing_trades = 0
            
#             # Store stats
#             stats_data = {
#                 'date': target_date,
#                 'symbol': symbol,
#                 'period': 'daily',
#                 'total_trades': total_trades,
#                 'winning_trades': winning_trades,
#                 'losing_trades': losing_trades,
#                 'net_profit': total_pnl,
#                 'commission_paid': total_commission,
#                 'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0
#             }
            
#             # Save to database
#             existing_stats = session.query(PerformanceStats).filter_by(
#                 date=target_date, symbol=symbol, period='daily'
#             ).first()
            
#             if existing_stats:
#                 for key, value in stats_data.items():
#                     if key not in ['date', 'symbol', 'period']:
#                         setattr(existing_stats, key, value)
#             else:
#                 stats = PerformanceStats(**stats_data)
#                 session.add(stats)
            
#             session.commit()
#             return stats_data
    
#     # ===================
#     # SYSTEM EVENTS
#     # ===================
    
#     def log_system_event(self, event_type: str, severity: str, message: str, 
#                         details: Dict[str, Any] = None, symbol: str = None, 
#                         strategy_name: str = None):
#         """Log system events, errors, connections"""
#         with self.get_session() as session:
#             event = SystemEvent(
#                 event_type=event_type,
#                 severity=severity,
#                 message=message,
#                 details=json.dumps(details) if details else None,
#                 symbol=symbol,
#                 strategy_name=strategy_name
#             )
#             session.add(event)
#             session.commit()
    
#     # ===================
#     # QUERIES
#     # ===================
    
#     def get_recent_signals(self, symbol: str, limit: int = 10) -> List[TradeSignal]:
#         """Get recent trade signals"""
#         with self.get_session() as session:
#             return session.query(TradeSignal).filter_by(symbol=symbol)\
#                          .order_by(TradeSignal.timestamp.desc()).limit(limit).all()
    
#     def get_current_position(self, symbol: str) -> Optional[Position]:
#         """Get current position for symbol"""
#         with self.get_session() as session:
#             return session.query(Position).filter_by(symbol=symbol).first()
    
#     def get_performance_summary(self, symbol: str, days: int = 30) -> Dict[str, Any]:
#         """Get performance summary for last N days"""
#         with self.get_session() as session:
#             stats = session.query(PerformanceStats).filter(
#                 PerformanceStats.symbol == symbol,
#                 PerformanceStats.period == 'daily',
#                 PerformanceStats.date >= date.today() - timedelta(days=days)
#             ).all()
            
#             if not stats:
#                 return {}
            
#             # Aggregate stats
#             total_trades = sum(s.total_trades for s in stats)
#             total_profit = sum(s.net_profit for s in stats)
#             total_commission = sum(s.commission_paid for s in stats)
            
#             return {
#                 'symbol': symbol,
#                 'period_days': days,
#                 'total_trades': total_trades,
#                 'total_profit': total_profit,
#                 'total_commission': total_commission,
#                 'avg_daily_profit': total_profit / len(stats) if stats else 0
#             } 