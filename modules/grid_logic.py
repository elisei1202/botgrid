"""
Grid Logic Module - Core Grid Strategy
Handles grid level calculation, recentering, and grid management
"""

import logging
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


def safe_float(value, default=0.0):
    """Safely convert value to float, return default if conversion fails"""
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


class GridLogic:
    """Manages grid trading strategy logic"""
    
    def __init__(
        self, 
        bybit_client,
        state_store,
        config: Dict
    ):
        self.client = bybit_client
        self.db = state_store
        self.config = config
        
        # Grid parameters
        self.symbol = config['trading']['symbol']
        self.category = config['trading']['category']
        
        # Current grid state
        self.center_price = 0.0
        self.buy_levels = []
        self.sell_levels = []
        self.active_orders = {}
        
        # Instrument info
        self.min_order_qty = 0.0
        self.qty_step = "0.1"
        self.tick_size = "0.0001"
        self.min_notional = 5.0
        
        # Recenter tracking
        self.last_recenter_time = datetime.utcnow()
        self.price_history = []
        self.max_history_points = 720  # 12 hours at 1 minute intervals
        
        logger.info("Grid Logic initialized")
    
    async def initialize(self):
        """Initialize grid logic and load instrument info"""
        await self._load_instrument_info()
        logger.info(f"Instrument info loaded for {self.symbol}")
        
        # Try to load last grid from database
        last_grid = await self.db.get_latest_grid()
        if last_grid:
            self.center_price = last_grid['center_price']
            logger.info(f"Loaded last grid from DB: center={self.center_price}")
        
    async def _load_instrument_info(self):
        """Load instrument specifications from Bybit"""
        try:
            info = await self.client.get_instruments_info(self.symbol, self.category)
            
            if not info:
                raise Exception("Failed to get instrument info")
            
            # Extract lot size filter
            lot_size_filter = info.get('lotSizeFilter', {})
            self.min_order_qty = float(lot_size_filter.get('minOrderQty', 1))
            self.qty_step = lot_size_filter.get('qtyStep', '1')
            self.min_notional = float(lot_size_filter.get('minNotionalValue', 5))
            
            # Extract price filter
            price_filter = info.get('priceFilter', {})
            self.tick_size = price_filter.get('tickSize', '0.0001')
            
            logger.info(f"Instrument specs: minQty={self.min_order_qty}, "
                       f"qtyStep={self.qty_step}, minNotional={self.min_notional}, "
                       f"tickSize={self.tick_size}")
            
        except Exception as e:
            logger.error(f"Error loading instrument info: {e}")
            raise
    
    async def get_current_price(self) -> float:
        """Get current mark price"""
        try:
            price = await self.client.get_mark_price(self.symbol, self.category)
            if price > 0:
                self.price_history.append({
                    'price': price,
                    'timestamp': datetime.utcnow()
                })
                
                # Trim history
                if len(self.price_history) > self.max_history_points:
                    self.price_history = self.price_history[-self.max_history_points:]
                
                return price
            return 0.0
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return 0.0
    
    def calculate_atr(self, period: int = 14) -> float:
        """Calculate ATR for dynamic grid spacing"""
        try:
            if len(self.price_history) < period * 2:
                return 0.0
            
            # Simple ATR approximation from price history
            prices = [p['price'] for p in self.price_history[-period * 2:]]
            ranges = []
            
            for i in range(1, len(prices)):
                high_low = abs(prices[i] - prices[i-1])
                ranges.append(high_low)
            
            if ranges:
                atr = np.mean(ranges)
                return atr
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0.0
    
    def get_grid_spacing(self, profile: str = "Normal") -> float:
        """Get grid spacing based on profile and volatility"""
        profile_config = self.config['grid']['profiles'].get(profile, 
                                                               self.config['grid']['profiles']['Normal'])
        base_spacing = profile_config['grid_spacing']
        
        # Adjust based on ATR if available
        atr = self.calculate_atr()
        if atr > 0 and self.center_price > 0:
            atr_pct = atr / self.center_price
            
            # If volatility is high, increase spacing slightly
            if atr_pct > 0.005:  # 0.5% ATR
                spacing = min(base_spacing * 1.2, self.config['grid']['grid_spacing_max'])
            else:
                spacing = base_spacing
        else:
            spacing = base_spacing
        
        return spacing
    
    def calculate_grid_levels(
        self, 
        center_price: float,
        profile: str = "Normal",
        available_capital: float = 100.0
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Calculate grid buy and sell levels
        Returns: (buy_levels, sell_levels)
        """
        
        profile_config = self.config['grid']['profiles'].get(profile,
                                                               self.config['grid']['profiles']['Normal'])
        
        target_buy_levels = profile_config['target_levels']
        target_sell_levels = profile_config['target_levels']
        spacing = self.get_grid_spacing(profile)
        
        # Auto-adjust levels for small capital
        # Ensure each level has at least minNotional ($5)
        min_budget_per_level = self.min_notional * 1.1  # Add 10% buffer
        max_possible_levels = int(available_capital / min_budget_per_level)
        
        if max_possible_levels < 2:
            logger.error(f"Capital ${available_capital:.2f} too small. Need at least ${min_budget_per_level * 2:.2f}")
            return [], []
        
        # Adjust levels if needed
        if max_possible_levels < (target_buy_levels + target_sell_levels):
            # Split evenly between buy and sell
            adjusted_levels = max_possible_levels // 2
            target_buy_levels = adjusted_levels
            target_sell_levels = adjusted_levels
            logger.warning(f"Capital limited - adjusted to {target_buy_levels} BUY + {target_sell_levels} SELL levels")
        
        logger.info(f"Calculating grid: center={center_price:.4f}, spacing={spacing*100:.2f}%, "
                   f"levels={target_buy_levels} BUY + {target_sell_levels} SELL")
        
        # Calculate budget per grid level
        total_levels = target_buy_levels + target_sell_levels
        budget_per_level = available_capital / total_levels
        
        logger.info(f"Budget per level: ${budget_per_level:.2f}")
        
        buy_levels = []
        sell_levels = []
        
        # Generate BUY levels (below center)
        for i in range(1, target_buy_levels + 1):
            price = center_price * (1 - spacing * i)
            price = float(self.client.format_price(price, self.tick_size))
            
            # Calculate quantity
            qty = self._calculate_order_qty(price, budget_per_level)
            
            if qty > 0 and qty * price >= self.min_notional:
                buy_levels.append({
                    'level': -i,
                    'price': price,
                    'qty': qty,
                    'side': 'Buy',
                    'notional': qty * price
                })
            else:
                logger.warning(f"Skipping BUY level {i}: qty={qty}, notional={qty*price:.2f} < min {self.min_notional}")
        
        # Generate SELL levels (above center)
        for i in range(1, target_sell_levels + 1):
            price = center_price * (1 + spacing * i)
            price = float(self.client.format_price(price, self.tick_size))
            
            # Calculate quantity
            qty = self._calculate_order_qty(price, budget_per_level)
            
            if qty > 0 and qty * price >= self.min_notional:
                sell_levels.append({
                    'level': i,
                    'price': price,
                    'qty': qty,
                    'side': 'Sell',
                    'notional': qty * price
                })
            else:
                logger.warning(f"Skipping SELL level {i}: qty={qty}, notional={qty*price:.2f} < min {self.min_notional}")
        
        # Validate we have at least some levels
        if not buy_levels and not sell_levels:
            logger.error(f"Failed to create any valid grid levels with ${available_capital:.2f}")
            return [], []
        
        # Log final grid
        total_buy_notional = sum(level['notional'] for level in buy_levels)
        total_sell_notional = sum(level['notional'] for level in sell_levels)
        total_notional = total_buy_notional + total_sell_notional
        
        logger.info(f"Grid calculated: {len(buy_levels)} BUY + {len(sell_levels)} SELL levels")
        logger.info(f"Total notional: ${total_notional:.2f} (buy=${total_buy_notional:.2f}, sell=${total_sell_notional:.2f})")
        
        return buy_levels, sell_levels
    
    def _calculate_order_qty(self, price: float, budget: float) -> float:
        """Calculate order quantity respecting minimums and steps"""
        
        # Calculate base quantity from budget
        qty = budget / price
        
        # Ensure minimum quantity
        qty = max(qty, self.min_order_qty)
        
        # Ensure minimum notional
        min_qty_for_notional = self.min_notional / price
        qty = max(qty, min_qty_for_notional)
        
        # Round to qty step
        qty_float = float(self.client.format_quantity(qty, self.qty_step))
        
        # Final validation
        if qty_float * price < self.min_notional:
            qty_float = min_qty_for_notional
            qty_float = float(self.client.format_quantity(qty_float, self.qty_step))
        
        return qty_float
    
    async def setup_grid(self, profile: str = "Normal") -> bool:
        """Setup initial grid with all orders"""
        try:
            # Get current price as center
            current_price = await self.get_current_price()
            if current_price <= 0:
                logger.error("Failed to get current price")
                return False
            
            self.center_price = current_price
            
            # Get available capital
            balance = await self.client.get_coin_balance("USDT")
            available_balance = safe_float(balance.get('availableToWithdraw', '0'), 0.0)
            
            if available_balance < self.config['trading']['initial_capital']:
                logger.warning(f"Insufficient balance: ${available_balance:.2f} < ${self.config['trading']['initial_capital']}")
                logger.info(f"Using configured initial capital: ${self.config['trading']['initial_capital']}")
            
            # Use configured initial capital
            capital = self.config['trading']['initial_capital']
            
            logger.info(f"Setting up grid with ${capital:.2f} capital")
            
            # Calculate grid levels
            self.buy_levels, self.sell_levels = self.calculate_grid_levels(
                self.center_price,
                profile,
                capital
            )
            
            if not self.buy_levels or not self.sell_levels:
                logger.error("Failed to calculate valid grid levels")
                return False
            
            # Cancel any existing orders first
            await self.client.cancel_all_orders(self.symbol, self.category)
            await asyncio.sleep(1)
            
            # Place all BUY orders
            buy_success = 0
            for level in self.buy_levels:
                try:
                    result = await self.client.place_order(
                        symbol=self.symbol,
                        side=level['side'],
                        order_type="Limit",
                        qty=str(level['qty']),
                        price=str(level['price']),
                        time_in_force="PostOnly",
                        category=self.category
                    )
                    
                    if result and 'orderId' in result:
                        order_id = result['orderId']
                        self.active_orders[order_id] = level
                        
                        # Save to database
                        await self.db.save_order({
                            'orderId': order_id,
                            'symbol': self.symbol,
                            'side': level['side'],
                            'price': level['price'],
                            'qty': level['qty'],
                            'orderType': 'Limit',
                            'orderStatus': 'New',
                            'grid_level': level['level']
                        })
                        
                        buy_success += 1
                        logger.info(f"BUY order placed: level={level['level']}, "
                                   f"price={level['price']:.4f}, qty={level['qty']}")
                    
                    await asyncio.sleep(0.1)  # Small delay between orders
                    
                except Exception as e:
                    logger.error(f"Error placing BUY order at level {level['level']}: {e}")
            
            # Place all SELL orders
            sell_success = 0
            for level in self.sell_levels:
                try:
                    result = await self.client.place_order(
                        symbol=self.symbol,
                        side=level['side'],
                        order_type="Limit",
                        qty=str(level['qty']),
                        price=str(level['price']),
                        time_in_force="PostOnly",
                        category=self.category
                    )
                    
                    if result and 'orderId' in result:
                        order_id = result['orderId']
                        self.active_orders[order_id] = level
                        
                        # Save to database
                        await self.db.save_order({
                            'orderId': order_id,
                            'symbol': self.symbol,
                            'side': level['side'],
                            'price': level['price'],
                            'qty': level['qty'],
                            'orderType': 'Limit',
                            'orderStatus': 'New',
                            'grid_level': level['level']
                        })
                        
                        sell_success += 1
                        logger.info(f"SELL order placed: level={level['level']}, "
                                   f"price={level['price']:.4f}, qty={level['qty']}")
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error placing SELL order at level {level['level']}: {e}")
            
            logger.info(f"Grid setup complete: {buy_success} BUY + {sell_success} SELL orders placed")
            
            # Save grid to history
            await self.db.save_grid_history({
                'center_price': self.center_price,
                'lowest_buy': self.buy_levels[-1]['price'] if self.buy_levels else 0,
                'highest_sell': self.sell_levels[-1]['price'] if self.sell_levels else 0,
                'num_buy_levels': len(self.buy_levels),
                'num_sell_levels': len(self.sell_levels),
                'grid_spacing': self.get_grid_spacing(profile),
                'reason': f'Initial setup with {profile} profile'
            })
            
            await self.db.log_event(
                'grid_setup',
                'INFO',
                f'Grid initialized with {len(self.buy_levels)} BUY + {len(self.sell_levels)} SELL levels',
                {'center_price': self.center_price, 'profile': profile}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up grid: {e}")
            return False
    
    async def should_recenter(self) -> Tuple[bool, str]:
        """
        Check if grid should be recentered based on ACTIVE orders from Bybit
        Returns: (should_recenter, reason)
        """
        
        current_price = await self.get_current_price()
        if current_price <= 0:
            return False, ""
        
        # Get ACTIVE orders from Bybit (not from memory)
        try:
            active_orders = await self.client.get_open_orders(
                self.symbol,
                self.category
            )
            
            if not active_orders or len(active_orders) == 0:
                # No active orders - should setup new grid
                return True, "No active orders found"
            
            # Extract buy and sell prices from ACTIVE orders
            buy_prices = []
            sell_prices = []
            
            for order in active_orders:
                side = order.get('side')
                price = safe_float(order.get('price', '0'), 0.0)
                
                if side == 'Buy':
                    buy_prices.append(price)
                elif side == 'Sell':
                    sell_prices.append(price)
            
            if not buy_prices or not sell_prices:
                return False, ""
            
            lowest_buy = min(buy_prices)
            highest_sell = max(sell_prices)
            
        except Exception as e:
            logger.error(f"Error checking active orders for recenter: {e}")
            return False, ""
        
        recenter_config = self.config['recenter']
        
        # ===== RECENTER CONDITIONS =====
        
        # 1. Price deviation check (2% - back to original)
        deviation_pct = recenter_config['price_deviation_pct']
        if current_price > highest_sell * (1 + deviation_pct):
            return True, f"Price {current_price:.4f} > highest sell {highest_sell:.4f} + {deviation_pct*100}%"
        
        if current_price < lowest_buy * (1 - deviation_pct):
            return True, f"Price {current_price:.4f} < lowest buy {lowest_buy:.4f} - {deviation_pct*100}%"
        
        # 2. Time-based recenter (48 hours - once every 2 days)
        hours_since_recenter = (datetime.utcnow() - self.last_recenter_time).total_seconds() / 3600
        time_threshold = recenter_config['time_based_hours']
        
        if hours_since_recenter >= time_threshold:
            return True, f"Time-based recenter: {hours_since_recenter:.1f}h >= {time_threshold}h"
        
        # 3. One-side dominance (24 hours - very patient)
        if len(self.price_history) >= 60:  # Need at least 1 hour of data
            recent_hours = recenter_config['one_side_hours']
            cutoff_time = datetime.utcnow() - timedelta(hours=recent_hours)
            
            recent_prices = [
                p for p in self.price_history 
                if p['timestamp'] >= cutoff_time
            ]
            
            if len(recent_prices) > 0:
                above_center = sum(1 for p in recent_prices if p['price'] > self.center_price)
                above_pct = above_center / len(recent_prices)
                
                if above_pct > 0.8:  # 80% of time above center
                    return True, f"Price above center {above_pct*100:.0f}% of last {recent_hours}h"
                
                if above_pct < 0.2:  # 80% of time below center
                    return True, f"Price below center {(1-above_pct)*100:.0f}% of last {recent_hours}h"
        
        # 4. Pump/dump detection (5% in 1 hour)
        if len(self.price_history) >= 60:
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            hour_ago_prices = [p for p in self.price_history if p['timestamp'] >= hour_ago]
            
            if len(hour_ago_prices) > 0:
                min_price = min(p['price'] for p in hour_ago_prices)
                max_price = max(p['price'] for p in hour_ago_prices)
                
                pump_pct = (max_price - min_price) / min_price
                threshold = recenter_config['pump_dump_pct']
                
                if pump_pct >= threshold:
                    return True, f"Pump/dump detected: {pump_pct*100:.1f}% in 1h"
        
        return False, ""
    
    async def recenter_grid(self, reason: str, profile: str = "Normal") -> bool:
        """Recenter the grid"""
        try:
            logger.info(f"Recentering grid. Reason: {reason}")
            
            # Log event
            await self.db.log_event(
                'recenter',
                'INFO',
                f'Grid recenter triggered: {reason}',
                {'old_center': self.center_price}
            )
            
            # Cancel all existing orders
            result = await self.client.cancel_all_orders(self.symbol, self.category)
            await asyncio.sleep(2)  # Wait for cancellations to process
            
            # Clear active orders
            self.active_orders.clear()
            
            # Setup new grid
            success = await self.setup_grid(profile)
            
            if success:
                self.last_recenter_time = datetime.utcnow()
                logger.info(f"Grid recentered successfully at {self.center_price:.4f}")
                return True
            else:
                logger.error("Failed to recenter grid")
                return False
                
        except Exception as e:
            logger.error(f"Error recentering grid: {e}")
            return False
    
    def get_grid_stats(self) -> Dict[str, Any]:
        """Get current grid statistics"""
        return {
            'center_price': self.center_price,
            'num_buy_levels': len(self.buy_levels),
            'num_sell_levels': len(self.sell_levels),
            'lowest_buy': self.buy_levels[-1]['price'] if self.buy_levels else 0,
            'highest_sell': self.sell_levels[-1]['price'] if self.sell_levels else 0,
            'total_active_orders': len(self.active_orders),
            'last_recenter': self.last_recenter_time.isoformat()
        }
