# 🏗️ Technical Architecture

## System Overview

The Bybit Grid Trading Bot is a Python-based automated trading system with the following architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                         Web UI (FastAPI)                     │
│                        Port 8000                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                    Main Orchestrator                         │
│                     (main.py)                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   Trading Loop                                        │  │
│  │   • Order Monitor                                     │  │
│  │   • Grid Monitor                                      │  │
│  │   • Risk Monitor                                      │  │
│  │   • Snapshot Service                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└───┬───────────┬──────────────┬──────────────┬─────────────┘
    │           │              │              │
    ↓           ↓              ↓              ↓
┌─────────┐ ┌────────────┐ ┌─────────────┐ ┌──────────────┐
│  Bybit  │ │   Grid     │ │    Risk     │ │    State     │
│ Client  │ │   Logic    │ │   Manager   │ │    Store     │
└────┬────┘ └─────┬──────┘ └──────┬──────┘ └──────┬───────┘
     │            │               │                │
     ↓            ↓               ↓                ↓
┌─────────────────────────────────────────────────────────────┐
│                    External Systems                          │
│  ┌─────────────────┐         ┌──────────────────┐          │
│  │  Bybit API      │         │   SQLite DB      │          │
│  │  (REST + WS)    │         │   (Persistence)  │          │
│  └─────────────────┘         └──────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Web UI Server (`ui_server.py`)

**Technology**: FastAPI + Jinja2 + Chart.js

**Responsibilities**:
- Serve web interface
- Provide REST API endpoints
- Handle user interactions
- Real-time data updates

**Key Endpoints**:
```
GET  /                    → Dashboard page
GET  /grid                → Grid levels page
GET  /positions           → Positions page
GET  /history             → Trade history page
GET  /settings            → Settings page

GET  /api/status          → Bot status
POST /api/start           → Start trading
POST /api/stop            → Stop trading
GET  /api/balance         → Wallet balance
GET  /api/positions       → Current positions
GET  /api/grid/levels     → Grid orders
GET  /api/trades/recent   → Trade history
GET  /api/pnl             → PnL summary
GET  /api/equity/chart    → Equity chart data
GET  /api/risk/metrics    → Risk metrics
POST /api/profile/change  → Change strategy
```

**Auto-refresh**: 5 seconds
**Port**: 8000 (configurable)

---

### 2. Main Orchestrator (`main.py`)

**Technology**: Python asyncio

**Responsibilities**:
- Coordinate all modules
- Manage bot lifecycle
- Run monitoring loops
- Handle graceful shutdown

**Async Tasks**:
```python
1. _monitor_orders()      # Checks for filled orders
   ├─ Frequency: Every 5 seconds
   └─ Action: Log trades, update DB

2. _monitor_grid()        # Checks recenter conditions
   ├─ Frequency: Every 60 seconds
   └─ Action: Recenter if needed

3. _monitor_risk()        # Tracks risk metrics
   ├─ Frequency: Every 60 seconds
   └─ Action: Activate kill-switch if needed

4. _take_snapshots()      # Saves equity data
   ├─ Frequency: Every 5 minutes
   └─ Action: Store snapshot for charts
```

---

### 3. Bybit Client (`modules/bybit_client.py`)

**Technology**: aiohttp + Bybit API v5

**Responsibilities**:
- Communicate with Bybit API
- Handle authentication (HMAC SHA256)
- Rate limiting (10 req/sec)
- Retry logic with exponential backoff

**Key Methods**:
```python
# Market Data
get_ticker()              # Current price
get_mark_price()          # Mark price
get_instruments_info()    # Symbol specs
get_kline()               # Candlestick data

# Account
get_wallet_balance()      # Total balance
get_coin_balance()        # Specific coin

# Trading
place_order()             # Create order
cancel_order()            # Cancel order
cancel_all_orders()       # Cancel all
get_open_orders()         # Active orders

# Positions
get_positions()           # All positions
get_position()            # Specific position
set_leverage()            # Set leverage
close_position()          # Market close
```

**Error Handling**:
- 10001 (Invalid qty) → Adjust and retry
- 110043 (Leverage error) → Skip leverage setting
- 100028 (Account forbidden) → Log and continue
- 10006 (Rate limit) → Exponential backoff

---

### 4. Grid Logic (`modules/grid_logic.py`)

**Responsibilities**:
- Calculate grid levels
- Place grid orders
- Monitor price movement
- Trigger recentering

**Grid Calculation**:
```python
def calculate_grid_levels(center_price, profile, capital):
    1. Get grid spacing from profile
    2. Adjust for volatility (ATR)
    3. Calculate buy levels: center × (1 - spacing × i)
    4. Calculate sell levels: center × (1 + spacing × i)
    5. Calculate qty per level: budget / price
    6. Validate minimums (qty, notional, step)
    7. Return valid levels
```

**Recenter Triggers**:
```python
1. Price Deviation
   if price > highest_sell × 1.02:  recenter()
   if price < lowest_buy × 0.98:    recenter()

2. Time-Based
   if hours_since_last_recenter >= 24:  recenter()

3. One-Side Dominance
   if 80% of time above/below center (10h):  recenter()

4. Pump/Dump
   if 5% movement in 1 hour:  recenter()
```

**ATR Calculation**:
```python
# Simple ATR from price history
ranges = [abs(price[i] - price[i-1]) for i in range(1, len(prices))]
atr = mean(ranges)
atr_pct = atr / current_price
```

---

### 5. Risk Manager (`modules/risk_manager.py`)

**Responsibilities**:
- Monitor exposure
- Track equity and drawdown
- Activate kill-switch
- Validate order sizes

**Max Exposure Check**:
```python
total_position_value = sum(size × mark_price for all positions)
exposure_pct = total_position_value / total_equity

if exposure_pct > max_exposure_pct:
    stop_new_orders()
```

**Kill-Switch Logic**:
```python
# Track daily max
if new_day:
    daily_max_equity = current_equity
else:
    daily_max_equity = max(daily_max_equity, current_equity)

# Check drawdown
drawdown = (daily_max_equity - current_equity) / daily_max_equity

if drawdown >= kill_switch_threshold:
    trigger_kill_switch()
    cancel_all_orders()
    stop_trading()
```

**Maker/Taker Check**:
```python
# Ensure PostOnly
if side == "Buy":
    if price >= best_ask:  # Would cross spread
        return False  # Risk of taker
        
if side == "Sell":
    if price <= best_bid:  # Would cross spread
        return False  # Risk of taker
```

---

### 6. State Store (`modules/state_store.py`)

**Technology**: aiosqlite (SQLite)

**Database Schema**:

```sql
-- Configuration
config (
    id, profile_name, symbol, grid_spacing,
    target_levels, profit_target, max_exposure_pct,
    leverage, is_active, created_at, updated_at
)

-- Grid History
grid_history (
    id, center_price, lowest_buy, highest_sell,
    num_buy_levels, num_sell_levels, grid_spacing,
    reason, created_at
)

-- Orders
orders (
    id, order_id, symbol, side, price, qty,
    order_type, status, grid_level,
    created_at, filled_at, canceled_at
)

-- Trades
trades (
    id, trade_id, order_id, symbol, side,
    price, qty, fee, fee_currency, is_maker,
    profit, grid_level, executed_at
)

-- Positions
positions (
    id, symbol, side, entry_price, size,
    mark_price, unrealized_pnl, leverage,
    opened_at, closed_at, close_price, realized_pnl
)

-- Equity Snapshots
equity_snapshots (
    id, total_equity, available_balance,
    unrealized_pnl, total_positions_value, snapshot_at
)

-- Events
events (
    id, event_type, severity, message,
    details, created_at
)

-- PnL Summary
pnl_summary (
    id, period, realized_pnl, unrealized_pnl,
    total_trades, winning_trades, losing_trades,
    total_fees, max_drawdown, calculated_at
)
```

---

## Data Flow

### Order Placement Flow
```
1. Grid Logic calculates levels
   ↓
2. Validate qty and notional
   ↓
3. Format price and qty to step
   ↓
4. Risk Manager validates size
   ↓
5. Bybit Client places order (PostOnly)
   ↓
6. State Store saves order
   ↓
7. Web UI displays order
```

### Order Fill Flow
```
1. Monitor detects filled order
   ↓
2. State Store saves trade
   ↓
3. Calculate profit (if grid close)
   ↓
4. Update position in database
   ↓
5. Web UI updates trades/positions
```

### Recenter Flow
```
1. Monitor checks conditions
   ↓
2. Trigger detected → Log event
   ↓
3. Cancel all existing orders
   ↓
4. Get current price as new center
   ↓
5. Calculate new grid levels
   ↓
6. Place all new orders
   ↓
7. Save grid to history
   ↓
8. Web UI updates grid display
```

---

## Configuration System

### config.yaml Structure
```yaml
api:           # Bybit API settings
trading:       # Symbol, capital, leverage
grid:          # Grid parameters and profiles
recenter:      # Recenter conditions
risk:          # Risk limits
orders:        # Order settings
rate_limit:    # API rate limiting
database:      # Database config
logging:       # Logging config
web_ui:        # Web UI settings
monitoring:    # Monitoring intervals
```

### Profile System
```python
profiles = {
    'Conservative': {
        'grid_spacing': 0.0035,    # 0.35%
        'target_levels': 5,
        'profit_target': 0.0030    # 0.30%
    },
    'Normal': {
        'grid_spacing': 0.0025,    # 0.25%
        'target_levels': 6,
        'profit_target': 0.0020    # 0.20%
    },
    'Aggressive': {
        'grid_spacing': 0.0015,    # 0.15%
        'target_levels': 8,
        'profit_target': 0.0015    # 0.15%
    }
}
```

---

## Security Architecture

### API Key Security
```
1. Stored in .env file (not in git)
2. Never logged or displayed
3. HMAC SHA256 signature for all requests
4. Recv window = 5000ms (prevents replay)
5. IP restriction recommended
```

### Order Security
```
1. PostOnly enforcement (no taker trades)
2. Max exposure limits
3. Kill-switch protection
4. Position size validation
5. Price deviation checks
```

### Web UI Security
```
1. No authentication (local use only)
2. Secret key for sessions
3. CORS enabled (configurable)
4. Input validation on settings
```

---

## Performance Characteristics

### Latency
- **Order placement**: 200-500ms
- **API calls**: 100-300ms
- **Database queries**: <10ms
- **UI refresh**: 5 seconds

### Resource Usage
- **Memory**: ~100-200 MB
- **CPU**: <5% (idle), 10-20% (active)
- **Disk**: ~10 MB (database grows with trades)
- **Network**: ~1-5 KB/s

### Scalability
- **Single symbol**: Optimized
- **Multiple symbols**: Would need threading
- **High frequency**: Rate limit is bottleneck
- **Long running**: No memory leaks

---

## Error Recovery

### Handled Errors
```python
1. Network failures
   → Retry with exponential backoff
   
2. API errors
   → Log, adjust parameters, continue
   
3. Invalid orders
   → Skip order, log warning
   
4. Database errors
   → Rollback, log, retry
```

### Unhandled Errors
```python
1. Critical system errors
   → Log and crash (requires restart)
   
2. Configuration errors
   → Fail fast on startup
```

---

## Testing Strategy

### Manual Testing Checklist
```
[ ] API connection test
[ ] Order placement
[ ] Order cancellation
[ ] Grid calculation
[ ] Recenter trigger
[ ] Risk limits
[ ] Kill-switch activation
[ ] Database persistence
[ ] Web UI functionality
[ ] Restart recovery
```

### Test on Testnet
```
1. Start with small capital
2. Run for 24-48 hours
3. Verify all features work
4. Check profit calculation
5. Test edge cases
6. Review logs for errors
```

---

## Deployment Architecture

### Single Server
```
Ubuntu Server
├── Python 3.8+
├── Virtual Environment
├── SQLite Database
├── Log Files
└── Web Server (port 8000)
```

### Production Considerations
```
1. Use systemd service
2. Setup log rotation
3. Regular database backups
4. Monitor disk space
5. Setup alerts (external)
6. Use reverse proxy (nginx)
7. SSL certificate (if remote)
```

---

## Monitoring Stack

### Built-in Monitoring
```
1. Logs (structured)
   ├─ INFO: Normal operations
   ├─ WARNING: Issues handled
   └─ ERROR: Failures

2. Database Events
   ├─ Recenter events
   ├─ Kill-switch triggers
   └─ API errors

3. Equity Snapshots
   └─ Track performance over time
```

### External Monitoring (Future)
```
1. Prometheus metrics
2. Grafana dashboards
3. Telegram alerts
4. Email notifications
5. SMS for critical events
```

---

## Development Guidelines

### Code Style
- PEP 8 compliant
- Type hints where beneficial
- Docstrings for all classes/methods
- Comments for complex logic

### Module Organization
```
modules/
├── __init__.py           # Package init
├── bybit_client.py       # External API
├── grid_logic.py         # Strategy
├── risk_manager.py       # Safety
└── state_store.py        # Persistence
```

### Adding New Features
```
1. Add configuration to config.yaml
2. Implement in appropriate module
3. Add database table if needed
4. Update Web UI endpoint
5. Update UI JavaScript
6. Document in README
7. Test thoroughly
```

---

This architecture is designed for:
✅ Reliability
✅ Maintainability
✅ Extensibility
✅ Performance
✅ Safety
