"""
State Store Module - SQLite Database Management
Handles all persistence for the Grid Trading Bot
"""

import aiosqlite
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class StateStore:
    """Manages bot state persistence in SQLite database"""
    
    def __init__(self, db_path: str = "data/grid_bot.db"):
        self.db_path = db_path
        self.db = None
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize database connection and create tables"""
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info(f"Database initialized at {self.db_path}")
        
    async def close(self):
        """Close database connection"""
        if self.db:
            await self.db.close()
            logger.info("Database connection closed")
            
    async def _create_tables(self):
        """Create all required database tables"""
        
        # Configuration table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                grid_spacing REAL NOT NULL,
                target_levels INTEGER NOT NULL,
                profit_target REAL NOT NULL,
                max_exposure_pct REAL NOT NULL,
                leverage INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Grid history table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS grid_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                center_price REAL NOT NULL,
                lowest_buy REAL NOT NULL,
                highest_sell REAL NOT NULL,
                num_buy_levels INTEGER NOT NULL,
                num_sell_levels INTEGER NOT NULL,
                grid_spacing REAL NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Orders table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                qty REAL NOT NULL,
                order_type TEXT NOT NULL,
                status TEXT NOT NULL,
                grid_level INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                filled_at TIMESTAMP,
                canceled_at TIMESTAMP
            )
        """)
        
        # Trades execution history
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE,
                order_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                qty REAL NOT NULL,
                fee REAL NOT NULL,
                fee_currency TEXT NOT NULL,
                is_maker BOOLEAN NOT NULL,
                profit REAL,
                grid_level INTEGER,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Positions table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                size REAL NOT NULL,
                mark_price REAL,
                unrealized_pnl REAL,
                leverage INTEGER,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                close_price REAL,
                realized_pnl REAL
            )
        """)
        
        # Equity snapshots for charts
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_equity REAL NOT NULL,
                available_balance REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                total_positions_value REAL NOT NULL,
                snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Events log (recenter, kill-switch, errors)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # PnL summary table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS pnl_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT NOT NULL,
                realized_pnl REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                winning_trades INTEGER NOT NULL,
                losing_trades INTEGER NOT NULL,
                total_fees REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.db.commit()
        logger.info("All database tables created successfully")
    
    # ============ CONFIG METHODS ============
    
    async def save_config(self, config: Dict[str, Any]):
        """Save or update active configuration"""
        try:
            # Deactivate all previous configs
            await self.db.execute("UPDATE config SET is_active = 0")
            
            # Insert new config
            await self.db.execute("""
                INSERT INTO config (
                    profile_name, symbol, grid_spacing, target_levels,
                    profit_target, max_exposure_pct, leverage, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                config.get('profile_name', 'Normal'),
                config['symbol'],
                config['grid_spacing'],
                config['target_levels'],
                config['profit_target'],
                config['max_exposure_pct'],
                config['leverage']
            ))
            
            await self.db.commit()
            logger.info(f"Configuration saved: {config.get('profile_name', 'Normal')}")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            await self.db.rollback()
            raise
    
    async def get_active_config(self) -> Optional[Dict[str, Any]]:
        """Get currently active configuration"""
        try:
            async with self.db.execute(
                "SELECT * FROM config WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting active config: {e}")
            return None
    
    # ============ GRID HISTORY METHODS ============
    
    async def save_grid_history(self, grid_data: Dict[str, Any]):
        """Save grid configuration to history"""
        try:
            await self.db.execute("""
                INSERT INTO grid_history (
                    center_price, lowest_buy, highest_sell,
                    num_buy_levels, num_sell_levels, grid_spacing, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                grid_data['center_price'],
                grid_data['lowest_buy'],
                grid_data['highest_sell'],
                grid_data['num_buy_levels'],
                grid_data['num_sell_levels'],
                grid_data['grid_spacing'],
                grid_data.get('reason', 'Initial setup')
            ))
            
            await self.db.commit()
            logger.info(f"Grid history saved: center={grid_data['center_price']}")
            
        except Exception as e:
            logger.error(f"Error saving grid history: {e}")
            await self.db.rollback()
    
    async def get_latest_grid(self) -> Optional[Dict[str, Any]]:
        """Get the most recent grid configuration"""
        try:
            async with self.db.execute(
                "SELECT * FROM grid_history ORDER BY created_at DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting latest grid: {e}")
            return None
    
    # ============ ORDER METHODS ============
    
    async def save_order(self, order: Dict[str, Any]):
        """Save order to database"""
        try:
            await self.db.execute("""
                INSERT OR IGNORE INTO orders (
                    order_id, symbol, side, price, qty,
                    order_type, status, grid_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order['orderId'],
                order['symbol'],
                order['side'],
                float(order['price']),
                float(order['qty']),
                order['orderType'],
                order['orderStatus'],
                order.get('grid_level')
            ))
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error saving order: {e}")
            await self.db.rollback()
    
    async def update_order_status(self, order_id: str, status: str, filled_at: datetime = None):
        """Update order status"""
        try:
            if filled_at:
                await self.db.execute("""
                    UPDATE orders SET status = ?, filled_at = ?
                    WHERE order_id = ?
                """, (status, filled_at, order_id))
            else:
                await self.db.execute("""
                    UPDATE orders SET status = ?
                    WHERE order_id = ?
                """, (status, order_id))
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            await self.db.rollback()
    
    async def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get all active orders"""
        try:
            async with self.db.execute("""
                SELECT * FROM orders
                WHERE status IN ('New', 'PartiallyFilled')
                ORDER BY price ASC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting active orders: {e}")
            return []
    
    # ============ TRADE METHODS ============
    
    async def save_trade(self, trade: Dict[str, Any]):
        """Save executed trade"""
        try:
            await self.db.execute("""
                INSERT OR IGNORE INTO trades (
                    trade_id, order_id, symbol, side, price, qty,
                    fee, fee_currency, is_maker, profit, grid_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.get('execId'),
                trade['orderId'],
                trade['symbol'],
                trade['side'],
                float(trade['execPrice']),
                float(trade['execQty']),
                float(trade.get('execFee', 0)),
                trade.get('feeRate', 'USDT'),
                trade.get('isMaker', True),
                trade.get('profit'),
                trade.get('grid_level')
            ))
            
            await self.db.commit()
            
            # Only log if it was actually inserted (not a duplicate)
            if self.db.total_changes > 0:
                logger.info(f"Trade saved: {trade['side']} {trade['execQty']} @ {trade['execPrice']}")
            
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            await self.db.rollback()
    
    async def get_trades_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get trade history for specified hours"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            async with self.db.execute("""
                SELECT * FROM trades
                WHERE executed_at >= ?
                ORDER BY executed_at DESC
            """, (cutoff,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting trades history: {e}")
            return []
    
    async def get_total_trades_count(self, hours: int = 24) -> int:
        """Get total number of trades in last N hours"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            async with self.db.execute("""
                SELECT COUNT(*) as count FROM trades
                WHERE executed_at >= ?
            """, (cutoff,)) as cursor:
                row = await cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Error getting trades count: {e}")
            return 0
    
    # ============ EQUITY SNAPSHOT METHODS ============
    
    async def save_equity_snapshot(self, snapshot: Dict[str, Any]):
        """Save equity snapshot for charts"""
        try:
            await self.db.execute("""
                INSERT INTO equity_snapshots (
                    total_equity, available_balance, unrealized_pnl, total_positions_value
                ) VALUES (?, ?, ?, ?)
            """, (
                snapshot['total_equity'],
                snapshot['available_balance'],
                snapshot['unrealized_pnl'],
                snapshot['total_positions_value']
            ))
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error saving equity snapshot: {e}")
            await self.db.rollback()
    
    async def get_equity_snapshots(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get equity snapshots for charts"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            async with self.db.execute("""
                SELECT * FROM equity_snapshots
                WHERE snapshot_at >= ?
                ORDER BY snapshot_at ASC
            """, (cutoff,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting equity snapshots: {e}")
            return []
    
    # ============ EVENT METHODS ============
    
    async def log_event(self, event_type: str, severity: str, message: str, details: Dict = None):
        """Log important events"""
        try:
            await self.db.execute("""
                INSERT INTO events (event_type, severity, message, details)
                VALUES (?, ?, ?, ?)
            """, (
                event_type,
                severity,
                message,
                json.dumps(details) if details else None
            ))
            
            await self.db.commit()
            logger.info(f"Event logged: {event_type} - {message}")
            
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            await self.db.rollback()
    
    async def get_recent_events(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            async with self.db.execute("""
                SELECT * FROM events
                WHERE created_at >= ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (cutoff, limit)) as cursor:
                rows = await cursor.fetchall()
                events = []
                for row in rows:
                    event = dict(row)
                    if event['details']:
                        event['details'] = json.loads(event['details'])
                    events.append(event)
                return events
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []
    
    # ============ PNL METHODS ============
    
    async def calculate_and_save_pnl(self, period: str = "24h"):
        """Calculate and save PnL summary"""
        try:
            # Map period to hours
            period_hours = {
                "24h": 24,
                "7d": 168,
                "30d": 720
            }
            hours = period_hours.get(period, 24)
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            # Get trades in period
            async with self.db.execute("""
                SELECT 
                    SUM(CASE WHEN profit > 0 THEN profit ELSE 0 END) as realized_pnl,
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(fee) as total_fees
                FROM trades
                WHERE executed_at >= ?
            """, (cutoff,)) as cursor:
                row = await cursor.fetchone()
                
                if row and row['total_trades']:
                    await self.db.execute("""
                        INSERT INTO pnl_summary (
                            period, realized_pnl, unrealized_pnl, total_trades,
                            winning_trades, losing_trades, total_fees, max_drawdown
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        period,
                        row['realized_pnl'] or 0,
                        0,  # Will be updated separately
                        row['total_trades'],
                        row['winning_trades'] or 0,
                        row['losing_trades'] or 0,
                        row['total_fees'] or 0,
                        0  # Will be calculated separately
                    ))
                    
                    await self.db.commit()
                    
        except Exception as e:
            logger.error(f"Error calculating PnL: {e}")
            await self.db.rollback()
    
    async def get_pnl_summary(self, period: str = "24h") -> Optional[Dict[str, Any]]:
        """Get PnL summary for period"""
        try:
            async with self.db.execute("""
                SELECT * FROM pnl_summary
                WHERE period = ?
                ORDER BY calculated_at DESC
                LIMIT 1
            """, (period,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting PnL summary: {e}")
            return None
