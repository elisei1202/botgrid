# 🤖 Bybit Grid Trading Bot - Render Edition

Bot de trading automatizat pentru Bybit Futures cu strategie GRID, optimizat pentru deployment pe Render.com.

## 🚀 Quick Deploy pe Render

### 1. Fork/Upload acest repo pe GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/USERNAME/bybit-grid-bot.git
git push -u origin main
```

### 2. Deploy pe Render

1. Mergi la [render.com](https://render.com) și Sign up
2. Click **"New +"** → **"Web Service"**
3. Connect repository
4. Setări automate din `render.yaml`:
   - **Region**: Frankfurt (EU)
   - **Plan**: Free
   - **Build**: `pip install -r requirements.txt`
   - **Start**: `python ui_server.py`

### 3. Configurează Environment Variables

În Render Dashboard → Environment, adaugă:

```env
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
ENVIRONMENT=mainnet
```

**Cum să obții API Key de pe Bybit:**
1. Login pe [Bybit](https://www.bybit.com)
2. Mergi la **API Management**
3. **Create New Key**
4. Permisiuni necesare:
   - ✅ Read-Write
   - ✅ Contract Trading
5. **IP Restriction**: Lasă gol pentru început (vei adăuga după deploy)

### 4. Deploy!

Click **"Create Web Service"** și așteaptă 2-3 minute.

### 5. Setup Keep-Alive (Important!)

**UptimeRobot** (Recomandat - FREE):
1. [uptimerobot.com](https://uptimerobot.com) → Sign up
2. **Add Monitor**:
   - Type: HTTP(s)
   - URL: `https://your-app.onrender.com/ping`
   - Interval: **5 minutes**
3. Done! ✅

## 📊 Accesare Dashboard

Deschide: `https://your-app.onrender.com`

## ⚙️ Configurare

Editează `config.yaml` pentru capital mic ($45-50):

```yaml
grid:
  profiles:
    Conservative:
      target_levels: 2  # 2 BUY + 2 SELL
```

## 💰 Total Cost: GRATIS ✅

---

**Made with ⚡ for Render.com**
