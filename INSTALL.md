# 📦 Installation Guide - Bybit Grid Trading Bot

Complete step-by-step installation guide for Ubuntu.

## Prerequisites Check

Before starting, ensure you have:
- ✅ Ubuntu 20.04 or later
- ✅ Python 3.8 or later
- ✅ Bybit account
- ✅ API credentials from Bybit
- ✅ Internet connection

## Step 1: System Preparation

### Update System
```bash
sudo apt update
sudo apt upgrade -y
```

### Install Required Packages
```bash
sudo apt install -y python3 python3-pip python3-venv git curl
```

### Verify Python Version
```bash
python3 --version
```
Should show Python 3.8 or higher.

## Step 2: Get Bybit API Credentials

1. **Login to Bybit**
   - Go to https://www.bybit.com
   - Login to your account

2. **Create API Key**
   - Navigate to: Account → API Management
   - Click "Create New Key"
   - Choose "System-generated API Keys"

3. **Configure Permissions**
   - ✅ Enable "Contract Trade"
   - ✅ Enable "Read-Write"
   - ❌ Disable "Transfer" (not needed)
   - ❌ Disable "Withdraw" (security)

4. **Save Credentials**
   - Copy API Key
   - Copy API Secret
   - ⚠️ Save these securely - you won't see the secret again!

5. **IP Restriction (Recommended)**
   - Add your server's IP address
   - Or use "Unrestricted" for testing (less secure)

## Step 3: Download and Setup Bot

### Clone or Download Project
If you have the project files, extract them:
```bash
cd /home/claude
# If files are in a zip:
unzip bybit_grid_bot.zip
cd bybit_grid_bot
```

### Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will take a few minutes. You should see packages installing:
- pybit
- fastapi
- uvicorn
- aiosqlite
- etc.

### Verify Installation
```bash
python -c "import fastapi, pybit; print('✓ Dependencies installed successfully')"
```

## Step 4: Configure the Bot

### Create Environment File
```bash
cp .env.example .env
nano .env
```

### Edit Configuration
Replace the placeholder values:
```env
BYBIT_API_KEY=YOUR_ACTUAL_API_KEY_HERE
BYBIT_API_SECRET=YOUR_ACTUAL_API_SECRET_HERE
ENVIRONMENT=testnet
SECRET_KEY=random_string_for_web_ui_security
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### Review Trading Config (Optional)
```bash
nano config.yaml
```

Key settings to check:
- `symbol`: XRPUSDT (or change to your preferred pair)
- `initial_capital`: 100 (adjust based on your capital)
- `testnet`: true (always test first!)

## Step 5: Test Connection

### Quick Connection Test
```bash
source venv/bin/activate
python -c "
from modules.bybit_client import BybitClient
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    client = BybitClient(
        os.getenv('BYBIT_API_KEY'),
        os.getenv('BYBIT_API_SECRET'),
        testnet=True
    )
    await client.initialize()
    
    # Test API connection
    ticker = await client.get_ticker('XRPUSDT', 'linear')
    if ticker:
        print(f'✓ Connection successful!')
        print(f'Current XRP price: \${ticker.get(\"markPrice\")}')
    else:
        print('✗ Connection failed')
    
    await client.close()

asyncio.run(test())
"
```

If successful, you'll see the current XRP price.

## Step 6: First Run

### Start the Web UI
```bash
./start.sh
```

Or manually:
```bash
source venv/bin/activate
python ui_server.py
```

### Access Web Interface
Open your browser and go to:
```
http://localhost:8000
```

Or from another computer on the same network:
```
http://YOUR_SERVER_IP:8000
```

### Initial Setup in Web UI
1. Check Dashboard - should see $0 balance initially
2. Go to Settings
3. Verify configuration shows XRPUSDT
4. Keep profile on "Normal" for first run

## Step 7: Fund Your Testnet Account

### Get Testnet Funds
1. Go to https://testnet.bybit.com
2. Login with your account
3. Navigate to "Assets"
4. Click "Get Testnet Funds"
5. Request USDT

You should receive test USDT within a few minutes.

### Verify Balance in Bot
Refresh the dashboard - you should now see your testnet balance.

## Step 8: Start Trading

### In Web UI:
1. Verify balance shows correctly
2. Check Settings one more time
3. Click "Start Trading" button
4. Bot will:
   - Calculate grid levels
   - Place buy orders below current price
   - Place sell orders above current price

### Monitor Initial Setup:
1. Go to "Grid Levels" page
2. You should see:
   - 6 buy orders (green)
   - 6 sell orders (red)
   - Current price indicator

## Step 9: Monitoring

### Dashboard Checks (Every Hour First Day)
- ✓ Total equity
- ✓ Number of active orders
- ✓ Any trades executed?
- ✓ PnL changes
- ✓ No error messages

### Important Indicators
- **Status badge**: Should show "Running" (green)
- **Active orders**: Should show ~12 orders
- **Exposure**: Should stay under 40%
- **Kill-switch**: Should show "Inactive"

### Log Monitoring
```bash
tail -f logs/grid_bot.log
```

Look for:
- ✓ "Order placed" messages
- ✓ "Order filled" messages
- ✗ Error messages (investigate if any)

## Step 10: Going to Mainnet (After Testing)

### ⚠️ Only After Successful Testnet Testing!

1. **Stop the bot**
   ```bash
   # Press Ctrl+C in terminal
   ```

2. **Create NEW API keys for mainnet**
   - Go to https://www.bybit.com (not testnet)
   - Create new API keys
   - Use same permissions as testnet

3. **Update configuration**
   ```bash
   nano .env
   ```
   
   Change:
   ```env
   ENVIRONMENT=mainnet
   BYBIT_API_KEY=your_mainnet_api_key
   BYBIT_API_SECRET=your_mainnet_api_secret
   ```

4. **Update config.yaml**
   ```bash
   nano config.yaml
   ```
   
   Change:
   ```yaml
   api:
     testnet: false
   ```

5. **Restart bot**
   ```bash
   ./start.sh
   ```

## Troubleshooting

### "Module not found" Error
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Permission denied" on start.sh
```bash
chmod +x start.sh
```

### "API key invalid"
- Check API key in .env file
- Ensure no spaces or quotes
- Verify API key is active in Bybit
- Check if using testnet key with testnet=true

### "Insufficient balance"
- For testnet: Request more testnet funds
- For mainnet: Deposit USDT to Unified account
- Check minimum is 50-100 USDT

### Bot stops immediately
```bash
# Check logs
cat logs/grid_bot.log

# Look for error messages
grep ERROR logs/grid_bot.log
```

### Can't access web UI
```bash
# Check if bot is running
ps aux | grep python

# Check port 8000
netstat -tuln | grep 8000

# Try accessing locally
curl http://localhost:8000
```

## System Service Setup (Optional)

To run bot as a system service:

```bash
sudo nano /etc/systemd/system/grid-bot.service
```

Add:
```ini
[Unit]
Description=Bybit Grid Trading Bot
After=network.target

[Service]
Type=simple
User=claude
WorkingDirectory=/home/claude/bybit_grid_bot
Environment="PATH=/home/claude/bybit_grid_bot/venv/bin"
ExecStart=/home/claude/bybit_grid_bot/venv/bin/python ui_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable grid-bot
sudo systemctl start grid-bot
sudo systemctl status grid-bot
```

## Security Recommendations

1. **API Keys**
   - Never share API keys
   - Use IP restrictions
   - Disable withdraw permissions

2. **Server Security**
   - Use firewall (ufw)
   - Keep system updated
   - Use SSH keys instead of passwords

3. **Bot Security**
   - Start with small capital
   - Monitor regularly first week
   - Keep testnet running in parallel

4. **Backups**
   ```bash
   # Backup database daily
   cp data/grid_bot.db data/backup_$(date +%Y%m%d).db
   ```

## Getting Help

If you encounter issues:

1. Check logs: `logs/grid_bot.log`
2. Verify configuration: `config.yaml` and `.env`
3. Test API connection
4. Check Bybit status: https://status.bybit.com
5. Review this guide again

## Next Steps

After successful installation:

1. ✅ Run on testnet for 24-48 hours
2. ✅ Monitor all trades
3. ✅ Understand how grid works
4. ✅ Try different profiles (Conservative/Aggressive)
5. ✅ Only then consider mainnet

---

**Remember: Start small, test thoroughly, never risk more than you can afford to lose!**
