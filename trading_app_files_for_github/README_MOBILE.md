# 📱 AlphaTrader Mobile - Autonomous Intraday Algo Trading App

> **Designed for Office Hours Execution:** Runs 24/7 in the Cloud even when your home PC is switched OFF. Monitored & controlled directly from your smartphone.

---

## 🌟 Key Mobile & Safety Features

1. **24/7 Cloud Execution (PC Can Be OFF)**:
   - The bot engine runs in the cloud (AWS / Render / Railway / PythonAnywhere) during market hours (09:15 - 15:30 IST).
   - Zero battery drain on your phone.
2. **Installable Smartphone App (PWA)**:
   - Open the web link in Chrome / Safari on Android or iPhone.
   - Tap **"Add to Home Screen"** to get a standalone native app icon with full-screen experience and splash screen.
3. **Office Safety PIN**:
   - 4-digit PIN lock screen protects against colleagues glancing at your screen or accidentally clicking buttons.
   - Default PIN: `1234` (can be customized in Settings).
4. **🚨 Emergency Kill Switch**:
   - High-visibility glowing red button. Closes 100% of open positions at market rate and halts trading instantly.
   - Requires 2-step confirmation to prevent accidental taps.
5. **🛡️ Daily Circuit Breaker (3% Max Loss)**:
   - Hard safety stop. If cumulative intraday losses reach 3% (e.g. -₹1,500 on ₹50,000 capital), the bot halts all trading for the rest of the day.
6. **⏰ Mandatory 15:15 IST Auto Square-Off**:
   - Automatically closes all intraday positions before market close (avoiding broker penalty auto-square-off charges).
7. **📲 Telegram Instant Push Alerts & Remote Control**:
   - Sound/vibrate alerts in your pocket for every Buy, Target Hit, Stop-Loss Hit, or Risk alert.
   - Remote control via phone commands: `/status`, `/squareoff`, `/kill`, `/pause`, `/resume`.
8. **⚡ 10%-15% Momentum Runners Screener**:
   - Dedicated tab scanning high-beta NSE stocks (`SUZLON`, `BEL`, `TRENT`, `INFY`, etc.) with Multi-Factor Confluence Scoring (0 to 100).

---

## 🚀 How to Run & Test (Locally on Phone via WiFi)

1. Double-click the desktop shortcut:
   `C:\Users\Kuldeep\Desktop\Run_Mobile_Trading_App.bat`
2. Look at the terminal output for your Mobile URL:
   ```text
   💻 Local PC URL   :  http://localhost:8000
   📱 Mobile Phone URL:  http://10.165.189.217:8000
   ```
3. Open `http://<your-ip>:8000` in your phone's browser (make sure phone is on the same WiFi network).
4. Enter PIN `1234` to unlock.
5. In Chrome/Safari, tap **Share / Settings -> Add to Home Screen** to install as an app!
6. Tap the **"Demo"** button anytime to watch a 3-second live simulation of a trade with P&L updates.

---

## ☁️ How to Deploy Free on Cloud (Runs When PC is OFF)

To keep the bot running while you are at the office with your home PC turned OFF:

### Method: Free 1-Click Deployment on Render.com
1. Create a free account at [https://render.com](https://render.com).
2. Create a private GitHub repository and push this folder (`c:\Users\Kuldeep\Downloads\trading app`).
3. On Render, click **New + -> Web Service** and select your repository.
4. Render will automatically detect `render.yaml` and configure:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Click **Deploy Web Service**.
6. Render will generate a free HTTPS URL like:
   `https://alphatrader-xxxx.onrender.com`
7. Open that URL on your smartphone browser, tap **"Add to Home Screen"**, and you have a 24/7 live trading app in your pocket!

---

## 📲 How to Connect Telegram Alerts (Optional)

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, choose a name and username, and copy the **HTTP API Token**.
3. Search for `@userinfobot` on Telegram to get your numeric **Chat ID**.
4. In the Mobile App under **Settings**, paste your Token and Chat ID, then tap **Save & Test Alert**.
5. You will now receive instant trade notifications and can use `/squareoff` from anywhere!
