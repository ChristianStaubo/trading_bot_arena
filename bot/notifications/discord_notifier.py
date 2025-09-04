# """
# Discord Notification System

# Sends clean, actionable alerts for:
# - Trade signals & executions
# - System errors & connection issues  
# - Daily/weekly performance summaries
# """

# import json
# import asyncio
# from datetime import datetime
# from typing import Dict, Any, Optional
# import aiohttp
# from dataclasses import dataclass


# @dataclass
# class NotificationConfig:
#     """Configuration for Discord notifications"""
#     webhook_url: str
#     username: str = "Trading Bot"
#     avatar_url: Optional[str] = None
    
#     # Notification preferences
#     send_signals: bool = True
#     send_executions: bool = True
#     send_errors: bool = True
#     send_daily_summary: bool = True
#     send_connection_events: bool = False


# class DiscordNotifier:
#     """Clean Discord webhook notifications for trading events"""
    
#     def __init__(self, config: NotificationConfig):
#         self.config = config
#         self.session: Optional[aiohttp.ClientSession] = None
    
#     async def __aenter__(self):
#         self.session = aiohttp.ClientSession()
#         return self
    
#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         if self.session:
#             await self.session.close()
    
#     async def send_trade_signal(self, signal_data: Dict[str, Any]):
#         """Send notification for new trade signal"""
#         if not self.config.send_signals:
#             return
        
#         symbol = signal_data['symbol']
#         action = signal_data['action']
#         price = signal_data['entry_price']
#         confidence = signal_data['confidence']
        
#         embed = {
#             "title": f"🚨 {action} Signal: {symbol}",
#             "color": 0x3498db if 'LONG' in action else 0xe74c3c,
#             "fields": [
#                 {"name": "Entry Price", "value": f"${price:.2f}", "inline": True},
#                 {"name": "Take Profit", "value": f"${signal_data['take_profit']:.2f}", "inline": True},
#                 {"name": "Stop Loss", "value": f"${signal_data['stop_loss']:.2f}", "inline": True},
#                 {"name": "Confidence", "value": confidence.title(), "inline": True},
#                 {"name": "Strategy", "value": signal_data['strategy_name'], "inline": True}
#             ],
#             "timestamp": datetime.utcnow().isoformat()
#         }
        
#         await self._send_embed(embed)
    
#     async def send_execution(self, execution_data: Dict[str, Any]):
#         """Send notification for trade execution"""
#         if not self.config.send_executions:
#             return
        
#         symbol = execution_data['symbol']
#         action = execution_data['action']
#         quantity = execution_data['quantity']
#         price = execution_data['price']
        
#         embed = {
#             "title": f"✅ Order Filled: {symbol}",
#             "color": 0x2ecc71,
#             "fields": [
#                 {"name": "Action", "value": action, "inline": True},
#                 {"name": "Quantity", "value": str(quantity), "inline": True},
#                 {"name": "Fill Price", "value": f"${price:.2f}", "inline": True},
#                 {"name": "Total Value", "value": f"${quantity * price:.2f}", "inline": True}
#             ],
#             "timestamp": datetime.utcnow().isoformat()
#         }
        
#         await self._send_embed(embed)
    
#     async def send_error(self, error_data: Dict[str, Any]):
#         """Send notification for system errors"""
#         if not self.config.send_errors:
#             return
        
#         severity = error_data['severity']
#         message = error_data['message']
        
#         # Color based on severity
#         colors = {
#             'warning': 0xf39c12,
#             'error': 0xe74c3c,
#             'critical': 0x992d22
#         }
        
#         embed = {
#             "title": f"⚠️ {severity.title()}: {error_data.get('event_type', 'System Error')}",
#             "color": colors.get(severity, 0xe74c3c),
#             "description": message,
#             "fields": [],
#             "timestamp": datetime.utcnow().isoformat()
#         }
        
#         # Add context if available
#         if 'symbol' in error_data:
#             embed['fields'].append({"name": "Symbol", "value": error_data['symbol'], "inline": True})
#         if 'details' in error_data:
#             embed['fields'].append({"name": "Details", "value": error_data['details'][:1000], "inline": False})
        
#         await self._send_embed(embed)
    
#     async def send_daily_summary(self, summary_data: Dict[str, Any]):
#         """Send daily performance summary"""
#         if not self.config.send_daily_summary:
#             return
        
#         stats = summary_data
#         win_rate = stats.get('win_rate', 0)
#         net_profit = stats.get('net_profit', 0)
#         total_trades = stats.get('total_trades', 0)
        
#         # Determine color based on performance
#         color = 0x2ecc71 if net_profit > 0 else 0xe74c3c if net_profit < 0 else 0x95a5a6
        
#         embed = {
#             "title": f"📊 Daily Summary: {stats.get('symbol', 'All Symbols')}",
#             "color": color,
#             "fields": [
#                 {"name": "Total Trades", "value": str(total_trades), "inline": True},
#                 {"name": "Win Rate", "value": f"{win_rate:.1f}%", "inline": True},
#                 {"name": "Net P&L", "value": f"${net_profit:.2f}", "inline": True},
#                 {"name": "Winning Trades", "value": str(stats.get('winning_trades', 0)), "inline": True},
#                 {"name": "Losing Trades", "value": str(stats.get('losing_trades', 0)), "inline": True},
#                 {"name": "Commission", "value": f"${stats.get('commission_paid', 0):.2f}", "inline": True}
#             ],
#             "timestamp": datetime.utcnow().isoformat()
#         }
        
#         await self._send_embed(embed)
    
#     async def send_connection_event(self, event_data: Dict[str, Any]):
#         """Send connection status notifications"""
#         if not self.config.send_connection_events:
#             return
        
#         event_type = event_data['event_type']
#         message = event_data['message']
        
#         icons = {
#             'connected': '🟢',
#             'disconnected': '🔴',
#             'reconnected': '🟡'
#         }
        
#         embed = {
#             "title": f"{icons.get(event_type, '🔘')} Connection {event_type.title()}",
#             "color": 0x2ecc71 if event_type == 'connected' else 0xe74c3c,
#             "description": message,
#             "timestamp": datetime.utcnow().isoformat()
#         }
        
#         await self._send_embed(embed)
    
#     async def _send_embed(self, embed: Dict[str, Any]):
#         """Send embed to Discord webhook"""
#         if not self.session:
#             return
        
#         payload = {
#             "username": self.config.username,
#             "embeds": [embed]
#         }
        
#         if self.config.avatar_url:
#             payload["avatar_url"] = self.config.avatar_url
        
#         try:
#             async with self.session.post(
#                 self.config.webhook_url,
#                 json=payload,
#                 headers={"Content-Type": "application/json"}
#             ) as response:
#                 if response.status != 204:
#                     print(f"Discord notification failed: {response.status}")
#         except Exception as e:
#             print(f"Discord notification error: {e}")


# # Usage example:
# """
# config = NotificationConfig(
#     webhook_url="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
#     send_signals=True,
#     send_executions=True,
#     send_errors=True,
#     send_daily_summary=True
# )

# async with DiscordNotifier(config) as notifier:
#     await notifier.send_trade_signal({
#         'symbol': 'ES',
#         'action': 'OPEN_LONG',
#         'entry_price': 4500.50,
#         'take_profit': 4520.00,
#         'stop_loss': 4485.00,
#         'confidence': 'high',
#         'strategy_name': 'bollinger_bands'
#     })
# """ 