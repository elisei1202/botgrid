"""
Web UI Server - FastAPI Application
Provides REST API and web interface for the Grid Trading Bot
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from main import GridTradingBot


def safe_float(value, default=0.0):
    """Safely convert value to float, return default if conversion fails"""
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Bybit Grid Trading Bot",
    description="Web UI for monitoring and controlling the grid trading bot",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Global bot instance
bot: Optional[GridTradingBot] = None
bot_task: Optional[asyncio.Task] = None


@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup"""
    global bot
    
    try:
        logger.info("Starting bot initialization...")
        bot = GridTradingBot()
        await bot.initialize()
        logger.info("✓ Bot initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global bot, bot_task
    
    if bot:
        await bot.shutdown()
    
    if bot_task and not bot_task.done():
        bot_task.cancel()


# ============ HEALTH CHECK (for Render/monitoring) ============

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring services like UptimeRobot
    Prevents Render free tier from spinning down
    """
    return {
        "status": "healthy",
        "bot_running": bot.running if bot else False,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "bybit-grid-bot",
        "version": "1.0.0"
    }


@app.get("/ping")
async def ping():
    """Simple ping endpoint for cron jobs"""
    return {"pong": True, "timestamp": datetime.utcnow().isoformat()}


# ============ WEB PAGES ============

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/grid", response_class=HTMLResponse)
async def grid_page(request: Request):
    """Grid levels page"""
    return templates.TemplateResponse("grid.html", {"request": request})


@app.get("/positions", response_class=HTMLResponse)
async def positions_page(request: Request):
    """Positions page"""
    return templates.TemplateResponse("positions.html", {"request": request})


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Trade history page"""
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    return templates.TemplateResponse("settings.html", {"request": request})


# ============ API ENDPOINTS ============

@app.get("/api/status")
async def get_status():
    """Get bot status"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        status = await bot.get_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/start")
async def start_bot():
    """Start trading"""
    global bot, bot_task
    
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    if bot.running:
        return {"status": "already_running", "message": "Bot is already running"}
    
    try:
        # Start bot in background task
        bot_task = asyncio.create_task(bot.start_trading())
        
        return {"status": "success", "message": "Trading started"}
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stop")
async def stop_bot():
    """Stop trading"""
    global bot, bot_task
    
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    if not bot.running:
        return {"status": "not_running", "message": "Bot is not running"}
    
    try:
        await bot.stop_trading()
        
        if bot_task and not bot_task.done():
            bot_task.cancel()
        
        return {"status": "success", "message": "Trading stopped"}
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/balance")
async def get_balance():
    """Get wallet balance"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        balance = await bot.client.get_coin_balance("USDT")
        wallet = await bot.client.get_wallet_balance()
        
        return {
            "available": safe_float(balance.get('availableToWithdraw', '0'), 0.0),
            "equity": safe_float(balance.get('equity', '0'), 0.0),
            "total_equity": safe_float(wallet.get('totalEquity', '0'), 0.0),
            "unrealized_pnl": safe_float(wallet.get('totalPerpUPL', '0'), 0.0)
        }
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/positions")
async def get_positions():
    """Get current positions"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        positions = await bot.client.get_positions(
            bot.config['trading']['symbol'],
            bot.config['trading']['category']
        )
        
        # Filter out empty positions
        active_positions = []
        for pos in positions:
            if safe_float(pos.get('size', '0'), 0.0) > 0:
                active_positions.append({
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'size': safe_float(pos.get('size', '0'), 0.0),
                    'entry_price': safe_float(pos.get('avgPrice', '0'), 0.0),
                    'mark_price': safe_float(pos.get('markPrice', '0'), 0.0),
                    'unrealized_pnl': safe_float(pos.get('unrealisedPnl', '0'), 0.0),
                    'leverage': pos.get('leverage', '1'),
                    'position_value': safe_float(pos.get('positionValue', '0'), 0.0)
                })
        
        return active_positions
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/grid/levels")
async def get_grid_levels():
    """Get current grid levels"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        # Get open orders
        orders = await bot.client.get_open_orders(
            bot.config['trading']['symbol'],
            bot.config['trading']['category']
        )
        
        # Get current price
        current_price = await bot.grid.get_current_price()
        
        # Format orders
        buy_orders = []
        sell_orders = []
        
        for order in orders:
            order_data = {
                'order_id': order['orderId'],
                'price': safe_float(order.get('price', '0'), 0.0),
                'qty': safe_float(order.get('qty', '0'), 0.0),
                'status': order['orderStatus'],
                'created_at': order['createdTime']
            }
            
            if order['side'] == 'Buy':
                buy_orders.append(order_data)
            else:
                sell_orders.append(order_data)
        
        # Sort orders
        buy_orders.sort(key=lambda x: x['price'], reverse=True)
        sell_orders.sort(key=lambda x: x['price'])
        
        return {
            'center_price': bot.grid.center_price,
            'current_price': current_price,
            'buy_orders': buy_orders,
            'sell_orders': sell_orders,
            'total_orders': len(orders)
        }
    except Exception as e:
        logger.error(f"Error getting grid levels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trades/recent")
async def get_recent_trades(hours: int = 24):
    """Get recent trades"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        trades = await bot.db.get_trades_history(hours)
        return trades
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pnl")
async def get_pnl(period: str = "24h"):
    """Get PnL summary"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        # Get trades in period
        period_map = {"24h": 24, "7d": 168, "30d": 720}
        hours = period_map.get(period, 24)
        
        trades = await bot.db.get_trades_history(hours)
        
        # Calculate PnL
        total_profit = sum(safe_float(t.get('profit', '0'), 0.0) for t in trades if t.get('profit'))
        total_fees = sum(safe_float(t.get('fee', '0'), 0.0) for t in trades)
        winning_trades = len([t for t in trades if safe_float(t.get('profit', '0'), 0.0) > 0])
        losing_trades = len([t for t in trades if safe_float(t.get('profit', '0'), 0.0) < 0])
        
        return {
            'period': period,
            'realized_pnl': total_profit,
            'total_fees': total_fees,
            'net_pnl': total_profit - total_fees,
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / len(trades) * 100) if trades else 0
        }
    except Exception as e:
        logger.error(f"Error getting PnL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/equity/chart")
async def get_equity_chart(hours: int = 24):
    """Get equity chart data"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        snapshots = await bot.db.get_equity_snapshots(hours)
        
        chart_data = []
        for snapshot in snapshots:
            chart_data.append({
                'timestamp': snapshot['snapshot_at'],
                'equity': safe_float(snapshot.get('total_equity', '0'), 0.0),
                'available': safe_float(snapshot.get('available_balance', '0'), 0.0),
                'unrealized_pnl': safe_float(snapshot.get('unrealized_pnl', '0'), 0.0)
            })
        
        return chart_data
    except Exception as e:
        logger.error(f"Error getting equity chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/metrics")
async def get_risk_metrics():
    """Get risk metrics"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        metrics = await bot.risk.get_risk_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error getting risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profile/change")
async def change_profile(profile: str):
    """Change trading profile"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    valid_profiles = ["Conservative", "Normal", "Aggressive"]
    if profile not in valid_profiles:
        raise HTTPException(status_code=400, detail=f"Invalid profile. Must be one of: {valid_profiles}")
    
    try:
        success = await bot.change_profile(profile)
        if success:
            return {"status": "success", "message": f"Profile changed to {profile}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to change profile")
    except Exception as e:
        logger.error(f"Error changing profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/killswitch/deactivate")
async def deactivate_killswitch():
    """Manually deactivate kill-switch"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        bot.risk.deactivate_kill_switch()
        
        await bot.db.log_event(
            'kill_switch',
            'INFO',
            'Kill-switch manually deactivated',
            {}
        )
        
        return {"status": "success", "message": "Kill-switch deactivated"}
    except Exception as e:
        logger.error(f"Error deactivating kill-switch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events/recent")
async def get_recent_events(hours: int = 24):
    """Get recent events"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        events = await bot.db.get_recent_events(hours)
        return events
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        config = await bot.db.get_active_config()
        return config if config else {}
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not bot:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": "Bot not initialized"}
        )
    
    return {
        "status": "healthy",
        "running": bot.running,
        "timestamp": datetime.utcnow().isoformat()
    }


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the web server"""
    logger.info(f"Starting web server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
