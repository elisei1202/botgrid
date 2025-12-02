"""
Risk Manager Module - Risk Management and Safety
Handles exposure limits, kill-switch, and risk monitoring
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def safe_float(value, default=0.0):
    """Safely convert value to float, return default if conversion fails"""
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


class RiskManager:
    """Manages trading risks and safety mechanisms"""
    
    def __init__(
        self,
        bybit_client,
        state_store,
        config: Dict
    ):
        self.client = bybit_client
        self.db = state_store
        self.config = config
        
        self.symbol = config['trading']['symbol']
        self.category = config['trading']['category']
        
        # Risk parameters
        self.max_exposure_pct = config['risk']['max_exposure_pct']
        self.kill_switch_drawdown_pct = config['risk']['kill_switch_drawdown_pct']
        self.max_position_size_pct = config['risk']['max_position_size_pct']
        
        # State tracking
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        self.daily_max_equity = 0.0
        self.last_equity_check = datetime.utcnow()
        
        # Exposure tracking
        self.current_exposure_usdt = 0.0
        self.total_equity_usdt = 0.0
        
        logger.info("Risk Manager initialized")
    
    async def update_equity_tracking(self):
        """Update equity tracking for drawdown calculation"""
        try:
            wallet = await self.client.get_wallet_balance()
            if not wallet:
                return
            
            total_equity = safe_float(wallet.get('totalEquity', '0'), 0.0)
            
            # Update daily max
            now = datetime.utcnow()
            if now.date() != self.last_equity_check.date():
                # New day - reset daily max
                self.daily_max_equity = total_equity
                logger.info(f"New day - reset daily max equity to ${total_equity:.2f}")
            else:
                # Update max if higher
                if total_equity > self.daily_max_equity:
                    self.daily_max_equity = total_equity
            
            self.total_equity_usdt = total_equity
            self.last_equity_check = now
            
            # Check for drawdown
            await self._check_drawdown()
            
        except Exception as e:
            logger.error(f"Error updating equity tracking: {e}")
    
    async def _check_drawdown(self):
        """Check if drawdown exceeds kill-switch threshold"""
        if self.daily_max_equity <= 0:
            return
        
        current_equity = self.total_equity_usdt
        drawdown = (self.daily_max_equity - current_equity) / self.daily_max_equity
        
        if drawdown >= self.kill_switch_drawdown_pct:
            reason = (f"Drawdown {drawdown*100:.2f}% exceeds threshold "
                     f"{self.kill_switch_drawdown_pct*100:.0f}% "
                     f"(Max: ${self.daily_max_equity:.2f}, Current: ${current_equity:.2f})")
            
            await self.trigger_kill_switch(reason)
    
    async def trigger_kill_switch(self, reason: str):
        """Activate kill-switch: cancel all orders and stop trading"""
        if self.kill_switch_active:
            return
        
        self.kill_switch_active = True
        self.kill_switch_reason = reason
        
        logger.critical(f"🚨 KILL-SWITCH ACTIVATED: {reason}")
        
        try:
            # Cancel all orders
            await self.client.cancel_all_orders(self.symbol, self.category)
            logger.info("All orders cancelled")
            
            # Log to database
            await self.db.log_event(
                'kill_switch',
                'CRITICAL',
                f'Kill-switch activated: {reason}',
                {
                    'equity': self.total_equity_usdt,
                    'daily_max': self.daily_max_equity,
                    'drawdown_pct': ((self.daily_max_equity - self.total_equity_usdt) / 
                                    self.daily_max_equity * 100) if self.daily_max_equity > 0 else 0
                }
            )
            
            # Close positions (optional - can be commented out if you want to keep positions)
            # positions = await self.client.get_positions(self.symbol, self.category)
            # for pos in positions:
            #     if safe_float(pos.get('size', '0'), 0.0) > 0:
            #         await self.client.close_position(self.symbol, self.category)
            #         logger.info(f"Position closed: {pos['side']}")
            
        except Exception as e:
            logger.error(f"Error during kill-switch activation: {e}")
    
    def deactivate_kill_switch(self):
        """Manually deactivate kill-switch (admin action)"""
        if self.kill_switch_active:
            logger.info("Kill-switch manually deactivated")
            self.kill_switch_active = False
            self.kill_switch_reason = ""
            
            # Reset daily max to current equity
            self.daily_max_equity = self.total_equity_usdt
    
    async def check_max_exposure(self) -> bool:
        """
        Check if current exposure exceeds maximum allowed
        Returns: True if within limits, False if exceeded
        """
        try:
            # Get current positions
            positions = await self.client.get_positions(self.symbol, self.category)
            
            total_position_value = 0.0
            for pos in positions:
                size = safe_float(pos.get('size', '0'), 0.0)
                if size > 0:
                    mark_price = safe_float(pos.get('markPrice', '0'), 0.0)
                    position_value = size * mark_price
                    total_position_value += position_value
            
            self.current_exposure_usdt = total_position_value
            
            # Get total equity
            wallet = await self.client.get_wallet_balance()
            if wallet:
                self.total_equity_usdt = safe_float(wallet.get('totalEquity', '0'), 0.0)
            
            if self.total_equity_usdt <= 0:
                logger.warning("Total equity is 0, cannot check exposure")
                return False
            
            # Calculate exposure percentage
            exposure_pct = self.current_exposure_usdt / self.total_equity_usdt
            
            if exposure_pct > self.max_exposure_pct:
                logger.warning(
                    f"⚠️ Max exposure exceeded: {exposure_pct*100:.1f}% > "
                    f"{self.max_exposure_pct*100:.0f}% "
                    f"(${self.current_exposure_usdt:.2f} / ${self.total_equity_usdt:.2f})"
                )
                
                await self.db.log_event(
                    'max_exposure',
                    'WARNING',
                    f'Maximum exposure exceeded: {exposure_pct*100:.1f}%',
                    {
                        'exposure_usdt': self.current_exposure_usdt,
                        'total_equity': self.total_equity_usdt,
                        'exposure_pct': exposure_pct * 100
                    }
                )
                
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking max exposure: {e}")
            return False
    
    async def validate_order_size(self, qty: float, price: float) -> bool:
        """Validate if order size is within position size limits"""
        try:
            order_value = qty * price
            
            if self.total_equity_usdt <= 0:
                wallet = await self.client.get_wallet_balance()
                if wallet:
                    self.total_equity_usdt = safe_float(wallet.get('totalEquity', '0'), 0.0)
            
            if self.total_equity_usdt <= 0:
                return False
            
            order_pct = order_value / self.total_equity_usdt
            
            if order_pct > self.max_position_size_pct:
                logger.warning(
                    f"Order size {order_pct*100:.1f}% exceeds max "
                    f"{self.max_position_size_pct*100:.0f}%"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating order size: {e}")
            return False
    
    async def check_order_as_maker(self, side: str, price: float) -> bool:
        """
        Check if order will be executed as MAKER
        Returns: True if safe (will be maker), False if might be taker
        """
        try:
            ticker = await self.client.get_ticker(self.symbol, self.category)
            if not ticker:
                return False
            
            best_bid = safe_float(ticker.get('bid1Price', '0'), 0.0)
            best_ask = safe_float(ticker.get('ask1Price', '0'), 0.0)
            
            if side == "Buy":
                # Buy order should be below best bid to be maker
                if price >= best_ask:
                    logger.warning(
                        f"BUY order at {price} would cross spread (ask={best_ask}) - TAKER risk"
                    )
                    return False
            
            elif side == "Sell":
                # Sell order should be above best ask to be maker
                if price <= best_bid:
                    logger.warning(
                        f"SELL order at {price} would cross spread (bid={best_bid}) - TAKER risk"
                    )
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking maker/taker: {e}")
            return True  # Allow order on error (PostOnly will protect)
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics"""
        try:
            # Update latest data
            await self.update_equity_tracking()
            await self.check_max_exposure()
            
            # Calculate metrics
            exposure_pct = (
                (self.current_exposure_usdt / self.total_equity_usdt * 100)
                if self.total_equity_usdt > 0 else 0
            )
            
            drawdown_pct = (
                ((self.daily_max_equity - self.total_equity_usdt) / self.daily_max_equity * 100)
                if self.daily_max_equity > 0 else 0
            )
            
            available_for_trading = (
                self.total_equity_usdt * self.max_exposure_pct - self.current_exposure_usdt
            )
            
            return {
                'kill_switch_active': self.kill_switch_active,
                'kill_switch_reason': self.kill_switch_reason,
                'total_equity': self.total_equity_usdt,
                'daily_max_equity': self.daily_max_equity,
                'current_exposure': self.current_exposure_usdt,
                'exposure_pct': exposure_pct,
                'max_exposure_pct': self.max_exposure_pct * 100,
                'current_drawdown_pct': drawdown_pct,
                'kill_switch_threshold_pct': self.kill_switch_drawdown_pct * 100,
                'available_for_trading': max(0, available_for_trading),
                'within_limits': (
                    exposure_pct <= self.max_exposure_pct * 100 and
                    drawdown_pct < self.kill_switch_drawdown_pct * 100
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            return {
                'error': str(e),
                'kill_switch_active': self.kill_switch_active
            }
    
    async def calculate_funding_impact(self) -> float:
        """Calculate estimated funding fee impact"""
        try:
            # Get current positions
            positions = await self.client.get_positions(self.symbol, self.category)
            
            total_funding_impact = 0.0
            
            for pos in positions:
                size = safe_float(pos.get('size', '0'), 0.0)
                if size > 0:
                    # Get funding rate (simplified - would need actual funding rate from API)
                    # Typical funding rate is around 0.01% every 8 hours
                    position_value = size * safe_float(pos.get('markPrice', '0'), 0.0)
                    daily_funding = position_value * 0.0001 * 3  # 3 funding periods per day
                    total_funding_impact += daily_funding
            
            return total_funding_impact
            
        except Exception as e:
            logger.error(f"Error calculating funding impact: {e}")
            return 0.0
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get overall safety status"""
        return {
            'safe_to_trade': not self.kill_switch_active,
            'kill_switch_active': self.kill_switch_active,
            'kill_switch_reason': self.kill_switch_reason,
            'exposure_ok': self.current_exposure_usdt <= self.total_equity_usdt * self.max_exposure_pct,
            'last_check': self.last_equity_check.isoformat()
        }
