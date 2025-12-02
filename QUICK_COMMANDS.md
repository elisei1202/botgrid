# Quick Commands Reference

## Initial Setup

```bash
# 1. Navigate to project
cd /home/claude/bybit_grid_bot

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Setup environment file
cp .env.example .env
nano .env  # Add your API credentials

# 6. Review configuration
nano config.yaml
```

## Running the Bot

```bash
# Option 1: Use start script (recommended)
./start.sh

# Option 2: Web UI + Bot
source venv/bin/activate
python ui_server.py

# Option 3: Bot only (terminal)
source venv/bin/activate
python main.py
```

## Access Web Interface

```bash
# Local access
http://localhost:8000

# Remote access
http://YOUR_SERVER_IP:8000
```

## Monitoring

```bash
# View live logs
tail -f logs/grid_bot.log

# View last 100 log lines
tail -n 100 logs/grid_bot.log

# Search for errors
grep ERROR logs/grid_bot.log

# Search for trades
grep "Order filled" logs/grid_bot.log
```

## Database Management

```bash
# Open database
sqlite3 data/grid_bot.db

# Show all tables
.tables

# View recent trades
SELECT * FROM trades ORDER BY executed_at DESC LIMIT 10;

# View active orders
SELECT * FROM orders WHERE status = 'New';

# View equity snapshots
SELECT * FROM equity_snapshots ORDER BY snapshot_at DESC LIMIT 20;

# Exit database
.quit

# Backup database
cp data/grid_bot.db data/backup_$(date +%Y%m%d_%H%M%S).db
```

## API Testing

```bash
# Check bot status
curl http://localhost:8000/api/status | python -m json.tool

# Check balance
curl http://localhost:8000/api/balance | python -m json.tool

# Check positions
curl http://localhost:8000/api/positions | python -m json.tool

# Check grid levels
curl http://localhost:8000/api/grid/levels | python -m json.tool

# Health check
curl http://localhost:8000/health
```

## Process Management

```bash
# Find running bot processes
ps aux | grep python

# Find process on port 8000
lsof -i :8000

# Kill process by PID
kill <PID>

# Force kill if needed
kill -9 <PID>
```

## System Service Commands

```bash
# If installed as service:

# Start service
sudo systemctl start grid-bot

# Stop service
sudo systemctl stop grid-bot

# Restart service
sudo systemctl restart grid-bot

# Check status
sudo systemctl status grid-bot

# Enable auto-start on boot
sudo systemctl enable grid-bot

# Disable auto-start
sudo systemctl disable grid-bot

# View service logs
sudo journalctl -u grid-bot -f
```

## Maintenance

```bash
# Update pip
pip install --upgrade pip

# Update all dependencies
pip install --upgrade -r requirements.txt

# Check disk space
df -h

# Check memory usage
free -h

# View system resources
htop
```

## Troubleshooting

```bash
# Test Python imports
python -c "import fastapi, pybit, aiosqlite; print('OK')"

# Test API connection
python -c "
from modules.bybit_client import BybitClient
import asyncio, os
from dotenv import load_dotenv

load_dotenv()
async def test():
    client = BybitClient(os.getenv('BYBIT_API_KEY'), os.getenv('BYBIT_API_SECRET'), testnet=True)
    await client.initialize()
    ticker = await client.get_ticker('XRPUSDT', 'linear')
    print(f'Price: {ticker.get(\"markPrice\")}' if ticker else 'Failed')
    await client.close()

asyncio.run(test())
"

# Check permissions
ls -la

# Fix permissions if needed
chmod +x start.sh
chmod -R 755 .

# Clear cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## Git Commands (if using version control)

```bash
# Initialize git
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit"

# Create .gitignore
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
.env
data/*.db
logs/*.log
*.db-journal
.DS_Store
EOF

# Push to remote
git remote add origin <your-repo-url>
git push -u origin main
```

## Backup Commands

```bash
# Full project backup
tar -czf bybit_bot_backup_$(date +%Y%m%d).tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='logs/*' \
    .

# Database only backup
cp data/grid_bot.db ~/backups/grid_bot_$(date +%Y%m%d).db

# Configuration backup
cp config.yaml ~/backups/config_$(date +%Y%m%d).yaml
cp .env ~/backups/env_$(date +%Y%m%d).bak
```

## Testing Commands

```bash
# Test database creation
source venv/bin/activate
python -c "
from modules.state_store import StateStore
import asyncio

async def test():
    db = StateStore('data/test.db')
    await db.initialize()
    print('Database initialized successfully')
    await db.close()

asyncio.run(test())
"

# Clean test database
rm data/test.db
```

## Performance Monitoring

```bash
# Monitor CPU and memory usage
watch -n 5 "ps aux | grep python | grep -v grep"

# Monitor network connections
netstat -tulpn | grep :8000

# Monitor disk I/O
iostat -x 5

# Monitor bot specific
watch -n 5 "curl -s http://localhost:8000/api/status | python -m json.tool | grep -E 'running|trades_24h|equity'"
```

## Quick Fixes

```bash
# Reset database (CAUTION: deletes all data)
rm data/grid_bot.db

# Clear all logs
rm logs/grid_bot.log

# Restart fresh
rm data/grid_bot.db logs/grid_bot.log
./start.sh

# Fix module not found
source venv/bin/activate
pip install -r requirements.txt

# Reset virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration Changes

```bash
# Switch to mainnet
nano .env
# Change: ENVIRONMENT=mainnet

nano config.yaml
# Change: testnet: false

# Change symbol
nano config.yaml
# Change: symbol: "BTCUSDT"

# Adjust capital
nano config.yaml
# Change: initial_capital: 200
```

## Emergency Commands

```bash
# Stop bot immediately
pkill -f "python ui_server.py"
pkill -f "python main.py"

# Cancel all orders via API (if bot is stuck)
# Manual API call would be needed here

# View last errors
tail -n 50 logs/grid_bot.log | grep ERROR

# Check if kill-switch activated
grep "kill.switch" logs/grid_bot.log
```

## Daily Commands

```bash
# Morning check
./daily_check.sh

# Create daily_check.sh script:
cat > daily_check.sh << 'EOF'
#!/bin/bash
echo "=== Daily Bot Check ==="
echo "Status:"
curl -s http://localhost:8000/api/status | python -m json.tool | grep -E "running|trades_24h"
echo ""
echo "Last 5 trades:"
tail -n 5 logs/grid_bot.log | grep "filled"
echo ""
echo "Errors today:"
grep "$(date +%Y-%m-%d)" logs/grid_bot.log | grep ERROR | wc -l
EOF

chmod +x daily_check.sh
```

## Help Commands

```bash
# List all available commands
cat QUICK_COMMANDS.md

# View README
cat README.md | less

# View installation guide
cat INSTALL.md | less

# Get Python help
python -c "from modules.bybit_client import BybitClient; help(BybitClient)"
```
