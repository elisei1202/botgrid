"""
Main Orchestrator - Grid Trading Bot
Coordinates all modules and runs the trading bot
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime
import yaml
from dotenv import load_dotenv
import os

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.bybit_client import BybitClient
from modules.state_store import StateStore
from modules.grid_logic import GridLogic
from modules.risk_manager import RiskManager


def safe_float(value, default=0.0):
    """Safely convert value to float, return default if conversion fails"""
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


# Configure logging
def setup_logging(config):
    """Setup structured logging"""
    log_level = getattr(logging, config['logging']['level'])
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory
    Path(config['logging']['log_file']).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(config['logging']['log_file']),
            logging.StreamHandler() if config['logging']['console_output'] else logging.NullHandler()
        ]
    )
    
    # Reduce noise from some libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class GridTradingBot:
    """Main Grid Trading Bot orchestrator"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        setup_logging(self.config)
        
        # Load environment variables
        # Try to load .env if exists (local development)
        # Otherwise use environment variables directly (Render/production)
        if os.path.exists('.env'):
            load_dotenv()
        
        self.api_key = os.getenv('BYBIT_API_KEY')
        self.api_secret = os.getenv('BYBIT_API_SECRET')
        
        # Check ENVIRONMENT variable for testnet/mainnet
        environment = os.getenv('ENVIRONMENT', 'testnet').lower()
        self.testnet = environment == 'testnet'
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found. Set BYBIT_API_KEY and BYBIT_API_SECRET environment variables")
        
        # Initialize modules
        self.client = None
        self.db = None
        self.grid = None
        self.risk = None
        
        # Bot state
        self.running = False
        self.active_profile = "Normal"
        
        logger.info("=" * 60)
        logger.info("🤖 Bybit Grid Trading Bot Initialized")
        logger.info(f"Symbol: {self.config['trading']['symbol']}")
        logger.info(f"Mode: {'TESTNET' if self.testnet else 'MAINNET'}")
        logger.info(f"Initial Capital: ${self.config['trading']['initial_capital']}")
        logger.info("=" * 60)
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def initialize(self):
        """Initialize all modules"""
        try:
            # Initialize database
            self.db = StateStore(self.config['database']['path'])
            await self.db.initialize()
            logger.info("✓ Database initialized")
            
            # Initialize Bybit client
            self.client = BybitClient(self.api_key, self.api_secret, self.testnet)
            await self.client.initialize()
            logger.info("✓ Bybit client initialized")
            
            # Initialize grid logic
            self.grid = GridLogic(self.client, self.db, self.config)
            await self.grid.initialize()
            logger.info("✓ Grid logic initialized")
            
            # Initialize risk manager
            self.risk = RiskManager(self.client, self.db, self.config)
            logger.info("✓ Risk manager initialized")
            
            # Load or create config
            active_config = await self.db.get_active_config()
            if active_config:
                self.active_profile = active_config['profile_name']
                logger.info(f"Loaded active profile: {self.active_profile}")
            else:
                # Save default config
                await self._save_current_config()
            
            logger.info("🚀 All modules initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def _save_current_config(self):
        """Save current configuration to database"""
        profile_config = self.config['grid']['profiles'][self.active_profile]
        
        await self.db.save_config({
            'profile_name': self.active_profile,
            'symbol': self.config['trading']['symbol'],
            'grid_spacing': profile_config['grid_spacing'],
            'target_levels': profile_config['target_levels'],
            'profit_target': profile_config['profit_target'],
            'max_exposure_pct': self.config['risk']['max_exposure_pct'],
            'leverage': self.config['trading']['leverage']
        })
    
    async def start_trading(self):
        """Start the trading bot"""
        if self.running:
            logger.warning("Bot is already running")
            return
        
        try:
            # Check if kill-switch is active
            if self.risk.kill_switch_active:
                logger.error("Cannot start: Kill-switch is active")
                return
            
            # Setup initial grid
            logger.info(f"Setting up grid with profile: {self.active_profile}")
            success = await self.grid.setup_grid(self.active_profile)
            
            if not success:
                logger.error("Failed to setup grid")
                return
            
            self.running = True
            logger.info("✓ Trading started successfully")
            
            # Start monitoring loops
            await asyncio.gather(
                self._monitor_orders(),
                self._monitor_grid(),
                self._monitor_risk(),
                self._take_snapshots()
            )
            
        except Exception as e:
            logger.error(f"Error starting trading: {e}")
            self.running = False
            raise
    
    async def stop_trading(self):
        """Stop the trading bot"""
        if not self.running:
            return
        
        logger.info("Stopping trading bot...")
        self.running = False
        
        # Cancel all orders
        await self.client.cancel_all_orders(
            self.config['trading']['symbol'],
            self.config['trading']['category']
        )
        
        logger.info("✓ Trading stopped")
    
    async def _monitor_orders(self):
        """Monitor and handle order fills"""
        logger.info("Starting order monitor...")
        
        while self.running:
            try:
                if self.risk.kill_switch_active:
                    await asyncio.sleep(10)
                    continue
                
                # Get filled orders
                executions = await self.client.get_executions(
                    self.config['trading']['symbol'],
                    self.config['trading']['category'],
                    limit=20
                )
                
                for exec_data in executions:
                    order_id = exec_data.get('orderId')
                    exec_id = exec_data.get('execId')
                    
                    # Check if we've already processed this execution
                    # (simplified - in production would check DB)
                    
                    side = exec_data.get('side')
                    price = safe_float(exec_data.get('execPrice', '0'), 0.0)
                    qty = safe_float(exec_data.get('execQty', '0'), 0.0)
                    
                    logger.info(f"📊 Order filled: {side} {qty} @ {price}")
                    
                    # Save trade to database
                    await self.db.save_trade({
                        'execId': exec_id,
                        'orderId': order_id,
                        'symbol': self.config['trading']['symbol'],
                        'side': side,
                        'execPrice': price,
                        'execQty': qty,
                        'execFee': safe_float(exec_data.get('execFee', '0'), 0.0),
                        'feeRate': exec_data.get('feeRate', 'USDT'),
                        'isMaker': exec_data.get('isMaker', True)
                    })
                    
                    # Update order status
                    await self.db.update_order_status(
                        order_id,
                        'Filled',
                        datetime.utcnow()
                    )
                    
                    # ===== GRID TP LOGIC - DISABLED =====
                    # TP automat dezactivat pentru capital mic
                    # Gridul clasic va închide pozițiile când prețul revine
                    # Pentru a activa TP-uri automate, decomentează linia de jos:
                    # await self._place_tp_order(side, price, qty)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in order monitor: {e}")
                await asyncio.sleep(10)
    
    async def _place_tp_order(self, filled_side: str, filled_price: float, qty: float):
        """
        Place take profit order after a grid order fills
        BUY filled -> place SELL TP above (closes LONG)
        SELL filled -> place BUY TP below (closes SHORT)
        All TPs are LIMIT + PostOnly = MAKER fees
        """
        try:
            # Get current grid spacing
            profile_config = self.config['grid']['profiles'][self.active_profile]
            profit_target = profile_config['profit_target']
            
            # Calculate TP price based on profit target
            if filled_side == 'Buy':
                # LONG opened, place SELL TP above
                tp_price = filled_price * (1 + profit_target)
                tp_side = 'Sell'
                logger.info(f"🎯 LONG opened @ {filled_price}, placing SELL TP @ {tp_price}")
            else:
                # SHORT opened, place BUY TP below
                tp_price = filled_price * (1 - profit_target)
                tp_side = 'Buy'
                logger.info(f"🎯 SHORT opened @ {filled_price}, placing BUY TP @ {tp_price}")
            
            # Format price and quantity
            tp_price = float(self.client.format_price(tp_price, self.grid.tick_size))
            qty_formatted = self.client.format_quantity(qty, self.grid.qty_step)
            
            # Verify minimum notional
            notional = float(qty_formatted) * tp_price
            if notional < self.grid.min_notional:
                logger.warning(f"TP notional ${notional:.2f} < min ${self.grid.min_notional}, skipping")
                return
            
            # Check if TP would be TAKER (crosses spread)
            maker_safe = await self.risk.check_order_as_maker(tp_side, tp_price)
            if not maker_safe:
                logger.warning(f"⚠️ TP at {tp_price} would be TAKER, adjusting...")
                # Adjust price to be safely in the book
                ticker = await self.client.get_ticker(
                    self.config['trading']['symbol'],
                    self.config['trading']['category']
                )
                if tp_side == 'Buy':
                    # Place below best bid
                    best_bid = safe_float(ticker.get('bid1Price', '0'), 0.0)
                    tp_price = best_bid * 0.9999  # Slightly below bid
                else:
                    # Place above best ask
                    best_ask = safe_float(ticker.get('ask1Price', '0'), 0.0)
                    tp_price = best_ask * 1.0001  # Slightly above ask
                
                tp_price = float(self.client.format_price(tp_price, self.grid.tick_size))
                logger.info(f"Adjusted TP price to {tp_price}")
            
            # Place TP order as LIMIT + PostOnly
            result = await self.client.place_order(
                symbol=self.config['trading']['symbol'],
                side=tp_side,
                order_type='Limit',
                qty=qty_formatted,
                price=str(tp_price),
                time_in_force='PostOnly',  # CRITICAL: Ensures MAKER fee
                category=self.config['trading']['category']
            )
            
            if result and 'orderId' in result:
                logger.info(f"✅ TP placed: {tp_side} {qty_formatted} @ {tp_price} (PostOnly/Maker)")
                
                # Save to database
                await self.db.save_order({
                    'orderId': result['orderId'],
                    'symbol': self.config['trading']['symbol'],
                    'side': tp_side,
                    'price': tp_price,
                    'qty': float(qty_formatted),
                    'orderType': 'Limit',
                    'orderStatus': 'New',
                    'grid_level': 0  # TP orders are level 0
                })
            elif result and 'error' in result:
                logger.error(f"Failed to place TP: {result['message']}")
            
        except Exception as e:
            logger.error(f"Error placing TP order: {e}")
    
    async def _monitor_grid(self):
        """Monitor grid and check for recenter conditions"""
        logger.info("Starting grid monitor...")
        
        while self.running:
            try:
                if self.risk.kill_switch_active:
                    await asyncio.sleep(30)
                    continue
                
                # Check if recenter is needed
                should_recenter, reason = await self.grid.should_recenter()
                
                if should_recenter:
                    logger.info(f"🔄 Recenter triggered: {reason}")
                    
                    # Check exposure before recentering
                    exposure_ok = await self.risk.check_max_exposure()
                    if not exposure_ok:
                        logger.warning("Skipping recenter: max exposure exceeded")
                        await asyncio.sleep(60)
                        continue
                    
                    # Recenter grid
                    success = await self.grid.recenter_grid(reason, self.active_profile)
                    if success:
                        logger.info("✓ Grid recentered successfully")
                    else:
                        logger.error("✗ Failed to recenter grid")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in grid monitor: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_risk(self):
        """Monitor risk metrics and kill-switch"""
        logger.info("Starting risk monitor...")
        
        while self.running:
            try:
                # Update equity and check drawdown
                await self.risk.update_equity_tracking()
                
                # Check exposure limits
                await self.risk.check_max_exposure()
                
                # Get risk metrics
                metrics = await self.risk.get_risk_metrics()
                
                # Log metrics periodically
                logger.debug(
                    f"Risk metrics: Equity=${metrics['total_equity']:.2f}, "
                    f"Exposure={metrics['exposure_pct']:.1f}%, "
                    f"Drawdown={metrics['current_drawdown_pct']:.2f}%"
                )
                
                # If kill-switch activated, stop trading
                if self.risk.kill_switch_active and self.running:
                    logger.critical("🚨 Kill-switch active - stopping trading")
                    await self.stop_trading()
                
                await asyncio.sleep(
                    self.config['monitoring']['health_check_interval_seconds']
                )
                
            except Exception as e:
                logger.error(f"Error in risk monitor: {e}")
                await asyncio.sleep(60)
    
    async def _take_snapshots(self):
        """Take periodic equity snapshots for charts"""
        logger.info("Starting snapshot service...")
        
        while self.running:
            try:
                # Get wallet data
                wallet = await self.client.get_wallet_balance()
                if wallet:
                    total_equity = safe_float(wallet.get('totalEquity', '0'), 0.0)
                    available = safe_float(wallet.get('availableToWithdraw', '0'), 0.0)
                    
                    # Get positions for unrealized PnL
                    positions = await self.client.get_positions(
                        self.config['trading']['symbol'],
                        self.config['trading']['category']
                    )
                    
                    unrealized_pnl = 0.0
                    total_position_value = 0.0
                    
                    for pos in positions:
                        if safe_float(pos.get('size', '0'), 0.0) > 0:
                            unrealized_pnl += safe_float(pos.get('unrealisedPnl', '0'), 0.0)
                            total_position_value += safe_float(pos.get('positionValue', '0'), 0.0)
                    
                    # Save snapshot
                    await self.db.save_equity_snapshot({
                        'total_equity': total_equity,
                        'available_balance': available,
                        'unrealized_pnl': unrealized_pnl,
                        'total_positions_value': total_position_value
                    })
                    
                    # Calculate and save PnL summaries
                    await self.db.calculate_and_save_pnl("24h")
                
                await asyncio.sleep(
                    self.config['monitoring']['snapshot_interval_minutes'] * 60
                )
                
            except Exception as e:
                logger.error(f"Error taking snapshot: {e}")
                await asyncio.sleep(300)
    
    async def change_profile(self, profile_name: str):
        """Change trading profile"""
        if profile_name not in self.config['grid']['profiles']:
            logger.error(f"Invalid profile: {profile_name}")
            return False
        
        logger.info(f"Changing profile to: {profile_name}")
        
        self.active_profile = profile_name
        await self._save_current_config()
        
        # Recenter grid with new profile
        if self.running:
            await self.grid.recenter_grid(
                f"Profile changed to {profile_name}",
                profile_name
            )
        
        return True
    
    async def get_status(self) -> dict:
        """Get current bot status"""
        try:
            # Get wallet balance
            balance = await self.client.get_coin_balance("USDT")
            available = safe_float(balance.get('availableToWithdraw', '0'), 0.0)
            equity = safe_float(balance.get('equity', '0'), 0.0)
            
            # Get positions
            positions = await self.client.get_positions(
                self.config['trading']['symbol'],
                self.config['trading']['category']
            )
            
            # Get grid stats
            grid_stats = self.grid.get_grid_stats()
            
            # Get risk metrics
            risk_metrics = await self.risk.get_risk_metrics()
            
            # Get recent trades count
            trades_24h = await self.db.get_total_trades_count(24)
            
            return {
                'running': self.running,
                'profile': self.active_profile,
                'symbol': self.config['trading']['symbol'],
                'balance': {
                    'available': available,
                    'equity': equity
                },
                'positions': len([p for p in positions if float(p.get('size', 0)) > 0]),
                'grid': grid_stats,
                'risk': risk_metrics,
                'trades_24h': trades_24h,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {'error': str(e)}
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down bot...")
        
        if self.running:
            await self.stop_trading()
        
        # Close connections
        if self.client:
            await self.client.close()
        
        if self.db:
            await self.db.close()
        
        logger.info("✓ Shutdown complete")


async def main():
    """Main entry point"""
    bot = None
    
    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        if bot:
            asyncio.create_task(bot.shutdown())
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create bot instance
        bot = GridTradingBot()
        
        # Initialize
        await bot.initialize()
        
        # Start trading
        await bot.start_trading()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        if bot:
            await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
