# 🚀 Pre-Deployment Checklist

## Before Starting Trading

### ✅ Prerequisites

- [ ] Ubuntu 20.04+ installed
- [ ] Python 3.8+ installed and verified
- [ ] Bybit account created
- [ ] API credentials obtained
- [ ] Understand grid trading basics
- [ ] Read full documentation (README.md)

### ✅ Installation

- [ ] Project downloaded and extracted
- [ ] Virtual environment created (`python3 -m venv venv`)
- [ ] Virtual environment activated (`source venv/bin/activate`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] No installation errors

### ✅ Configuration

- [ ] `.env` file created from `.env.example`
- [ ] API Key added to `.env`
- [ ] API Secret added to `.env`
- [ ] Environment set to `testnet` initially
- [ ] Secret key generated for web UI
- [ ] `config.yaml` reviewed
- [ ] Symbol configured (default: XRPUSDT)
- [ ] Initial capital set appropriately
- [ ] Leverage kept at 1x
- [ ] Risk parameters understood

### ✅ API Setup

- [ ] API key has "Contract Trade" permission
- [ ] API key has "Read-Write" permission
- [ ] IP restriction configured (if needed)
- [ ] **Withdraw permission DISABLED** (security)
- [ ] **Transfer permission DISABLED** (security)
- [ ] API key tested and working

### ✅ Connection Test

- [ ] Bot can connect to Bybit API
- [ ] Current price retrieved successfully
- [ ] Balance information accessible
- [ ] No authentication errors
- [ ] Rate limiting working

### ✅ Testnet Setup

- [ ] Testnet account funded
- [ ] Testnet balance visible in bot
- [ ] Testnet balance > minimum capital
- [ ] Symbol available on testnet
- [ ] Orders can be placed on testnet

## First Run

### ✅ Initial Start

- [ ] Bot starts without errors
- [ ] Web UI accessible at localhost:8000
- [ ] Dashboard loads correctly
- [ ] Balance shown correctly
- [ ] All pages accessible
- [ ] No JavaScript errors in browser

### ✅ Configuration Check

- [ ] Settings page shows correct profile
- [ ] Symbol is correct
- [ ] Capital amount is correct
- [ ] Risk limits are acceptable
- [ ] Profile settings understood

### ✅ Grid Setup

- [ ] "Start Trading" button clicked
- [ ] Bot status changes to "Running"
- [ ] Grid orders placed successfully
- [ ] Buy orders visible (6 orders below center)
- [ ] Sell orders visible (6 orders above center)
- [ ] Order prices calculated correctly
- [ ] Total orders = 12 (Normal profile)
- [ ] No order errors in logs

### ✅ Monitoring - First Hour

- [ ] Dashboard updates every 5 seconds
- [ ] Current price updates
- [ ] Active orders count is correct
- [ ] Equity tracked correctly
- [ ] No error messages
- [ ] Logs showing normal activity
- [ ] Grid visualization makes sense

## 24 Hour Testing Period

### ✅ Day 1 Checks (Every 2-3 Hours)

**Morning Check:**
- [ ] Bot still running
- [ ] Status = "Running"
- [ ] Orders still active
- [ ] Balance unchanged (if no trades)
- [ ] No errors in logs

**Afternoon Check:**
- [ ] Any trades executed?
- [ ] If yes: trades visible in History
- [ ] Profit calculations correct
- [ ] New orders placed after fills
- [ ] PnL calculation working
- [ ] Grid recentered if needed

**Evening Check:**
- [ ] Full day stats available
- [ ] 24h trades count
- [ ] 24h PnL shown
- [ ] Equity chart populated
- [ ] No kill-switch triggers
- [ ] Exposure within limits

### ✅ Grid Behavior Verification

- [ ] Orders fill in both directions (buy and sell)
- [ ] Grid recenters automatically when needed
- [ ] New orders placed after recenter
- [ ] Old orders cancelled before recenter
- [ ] Grid stays centered around price
- [ ] Distance between levels consistent

### ✅ Risk Management Verification

- [ ] Exposure stays under 40%
- [ ] No single position > 20%
- [ ] Kill-switch inactive
- [ ] Daily max equity tracked
- [ ] Drawdown calculated correctly
- [ ] Stop if drawdown > 10% (test if possible)

### ✅ Performance Verification

- [ ] All orders are maker (PostOnly)
- [ ] Fees are negative (maker rebates)
- [ ] Profit per grid ≈ grid spacing
- [ ] No taker orders executed
- [ ] Order fills at limit prices
- [ ] Slippage minimal/none

## Week 1 Testing

### ✅ Weekly Checks

**Performance:**
- [ ] Total trades > 10
- [ ] Win rate > 40%
- [ ] Net PnL positive
- [ ] Maker fee rebates received
- [ ] Grid recentered at least once
- [ ] No manual intervention needed

**Stability:**
- [ ] Bot ran continuously
- [ ] No crashes or restarts
- [ ] Database growing normally
- [ ] Logs manageable size
- [ ] No memory leaks
- [ ] CPU usage stable

**Edge Cases:**
- [ ] Handled price spike correctly
- [ ] Recentered on volatility
- [ ] Maintained grid during slow market
- [ ] No stuck orders
- [ ] All orders cancelled/filled or recentered

## Before Mainnet

### ✅ Final Testnet Verification

- [ ] Ran on testnet for at least 7 days
- [ ] Profitable on testnet overall
- [ ] No critical bugs found
- [ ] All features working as expected
- [ ] Logs reviewed thoroughly
- [ ] Database backup created
- [ ] Configuration finalized

### ✅ Understanding Confirmation

- [ ] Understand how grid works
- [ ] Know when grid recenters
- [ ] Understand risk limits
- [ ] Know what kill-switch does
- [ ] Can read and interpret logs
- [ ] Can use Web UI confidently
- [ ] Know how to stop bot safely

### ✅ Mainnet Preparation

- [ ] NEW API keys created for mainnet
- [ ] Mainnet API keys tested
- [ ] Initial capital decided (start small!)
- [ ] Risk tolerance confirmed
- [ ] Stop-loss plan defined
- [ ] Monitoring plan established
- [ ] Emergency procedures understood

## Mainnet Deployment

### ✅ Configuration Change

- [ ] `.env` updated with mainnet API keys
- [ ] `config.yaml` set testnet: false
- [ ] Initial capital set conservatively
- [ ] Profile selection confirmed (start Normal)
- [ ] Risk limits appropriate
- [ ] All settings double-checked

### ✅ Mainnet Start

- [ ] Old bot stopped
- [ ] Configuration verified again
- [ ] Real balance confirmed in Web UI
- [ ] **Start with small capital first!**
- [ ] Orders placed successfully
- [ ] Grid looks correct
- [ ] All systems green

### ✅ First Trade on Mainnet

- [ ] First order filled
- [ ] Real money trade confirmed
- [ ] PnL calculated correctly
- [ ] Emotions in check
- [ ] Monitoring actively
- [ ] Everything working as expected

## Ongoing Monitoring

### ✅ Daily Tasks

- [ ] Check bot status (morning)
- [ ] Review overnight activity
- [ ] Check PnL progression
- [ ] Verify no errors in logs
- [ ] Confirm exposure within limits
- [ ] Check recent trades
- [ ] Verify grid still active

### ✅ Weekly Tasks

- [ ] Review 7-day performance
- [ ] Analyze win rate
- [ ] Check total fees paid/earned
- [ ] Database backup
- [ ] Log file rotation
- [ ] Check disk space
- [ ] Review configuration

### ✅ Monthly Tasks

- [ ] Full performance analysis
- [ ] Consider profile adjustments
- [ ] Review grid spacing effectiveness
- [ ] Update dependencies if needed
- [ ] System maintenance
- [ ] Strategy optimization

## Red Flags 🚩

### Stop and investigate immediately if:

- [ ] Kill-switch activated unexpectedly
- [ ] Exposure > 60%
- [ ] Multiple errors in short time
- [ ] Orders not filling at all
- [ ] PnL declining consistently
- [ ] Taker fees charged
- [ ] Bot crashes repeatedly
- [ ] Unusual API errors
- [ ] Database corruption
- [ ] Memory/CPU spikes

## Safety Reminders

### ⚠️ Critical Rules

1. **Always test on testnet first** - No exceptions!
2. **Start with small capital** - You can always add more
3. **Never use max leverage** - Keep it at 1x initially
4. **Don't modify code without testing** - Test changes on testnet
5. **Keep funds secure** - Use IP restrictions, disable withdraw
6. **Monitor regularly** - Especially first 2 weeks
7. **Understand risks** - Grid can lose money in trending markets
8. **Have exit plan** - Know when to stop

### 💡 Best Practices

1. Run testnet bot in parallel to mainnet
2. Keep detailed notes of changes
3. Backup database before changes
4. Start Conservative, move to Normal after comfort
5. Don't chase losses by switching to Aggressive
6. Review logs weekly
7. Keep learning about grid trading
8. Join trading communities for insights

## Final Verification

Before clicking "Start Trading" on mainnet:

- [ ] I have tested thoroughly on testnet
- [ ] I understand how the bot works
- [ ] I have read all documentation
- [ ] I have appropriate capital allocated
- [ ] I accept the risks involved
- [ ] I know how to stop the bot
- [ ] I have backup plan if things go wrong
- [ ] I will monitor actively initially
- [ ] I will not panic on drawdowns
- [ ] I understand this is not guaranteed profit

## Emergency Contacts

**If something goes wrong:**

1. **Stop the bot**: `Ctrl+C` or click "Stop Trading"
2. **Check logs**: `logs/grid_bot.log`
3. **Review last actions**: Check Events in Web UI
4. **Verify balance**: Log into Bybit directly
5. **Cancel orders manually**: If bot won't stop, use Bybit UI
6. **Ask for help**: Check documentation, community forums

## Success Indicators

✅ Bot is working well if:
- Running continuously without crashes
- Executing trades in both directions
- Maintaining appropriate exposure
- PnL positive over time (realistic expectations)
- All orders are maker
- Grid recentering appropriately
- Logs show normal activity
- Kill-switch never triggered
- You sleep well at night 😊

---

## Sign-Off

**I confirm that I have:**
- [ ] Read and understood all documentation
- [ ] Completed testnet testing successfully
- [ ] Verified all items in this checklist
- [ ] Understood the risks involved
- [ ] Set up with appropriate capital
- [ ] Established monitoring routine

**Date:** _______________
**Capital Allocated:** $ _______________
**Profile Selected:** _______________

---

**Remember: Trading cryptocurrencies involves substantial risk. Never invest more than you can afford to lose. This bot is a tool, not a guarantee of profit.**

**Good luck and trade responsibly! 🚀**
