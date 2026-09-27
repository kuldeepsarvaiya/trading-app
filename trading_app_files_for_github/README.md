# ⚡ Intraday Stock Buying Algorithmic Trading Bot

An end-to-end, production-ready algorithmic trading system designed for **daily intraday stock buying**. Built with a systematic Opening Range Breakout (ORB) + VWAP + Momentum strategy, institutional-grade risk management (1% risk rule, dynamic position sizing, ATR trailing stop-loss, daily drawdown circuit breaker), and automated intraday lifecycle with mandatory market square-off.

---

## 🎯 Key Features

- **High-Probability Intraday Strategy**:
  - **15-Min Opening Range Breakout (ORB)**: Evaluates high-liquidity morning session breakout.
  - **Intraday VWAP Filter**: Guarantees institutional buying bias (Price > VWAP).
  - **EMA Alignment**: Fast EMA (9) > Slow EMA (21) trend confirmation.
  - **Institutional Volume Expansion**: Filters out fake breakouts by requiring candle volume $\ge 1.3\times$ 20-period Average Volume.
  - **RSI Momentum Corridor**: Validates healthy momentum between 52 and 75 RSI.
- **Strict Risk Management**:
  - **1% Capital Risk Per Trade**: Dynamically sizes shares based on Stop-Loss distance ($\text{Qty} = \lfloor \frac{\text{Capital} \times 1\%}{\text{Entry} - \text{SL}} \rfloor$).
  - **3% Daily Circuit Breaker**: Halts all trading and closes active trades if cumulative daily loss reaches $3\%$.
  - **Minimum 1:2 Risk-to-Reward Ratio**: Strictly rejects trades with inadequate reward potential.
  - **Dynamic Trailing Stop Loss**: Locks profit to Break-Even at $+1R$ and trails via ATR at $+1.5R$. Stop loss ratchets strictly upwards.
  - **Max Concurrent Positions**: Prevents overexposure (default max 3 open positions).
- **Intraday Lifecycle Management**:
  - `09:15 - 09:30`: Morning session open & 15-min Opening Range baseline calculation.
  - `09:30 - 11:30`: Prime liquidity entry window.
  - `11:30 - 15:15`: Position management and trailing stop monitoring.
  - `15:15`: **Mandatory Auto Square-Off** (closes all open positions before market close to avoid overnight risk).
- **Realistic Paper Trading Simulator**:
  - Built-in simulation with realistic slippage ($0.03\%$) and statutory taxes/brokerage ($0.03\%$).
- **Live Terminal Dashboard**:
  - Real-time colorized monitoring using `rich` displaying portfolio capital, open positions, unrealized P&L, and trade audits.
- **Fast Historical Backtesting**:
  - Event-driven multi-day simulation with win rate, profit factor, Sharpe/drawdown metrics, and trade breakdowns.

---

## 🏗️ Project Architecture

```
intraday-algo-bot/
├── config/
│   ├── config.yaml          # Capital, risk %, market timings, strategy parameters
│   └── symbols.csv          # Liquid stock watchlist (NSE & US equities)
├── core/
│   ├── config_loader.py     # Typed configuration loader and validator
│   ├── models.py            # Order, Position, Candle, Signal, Trade data classes
│   └── logger.py            # Rich console logger and file audit logging
├── data/
│   ├── data_feed.py         # Historical and live data fetcher (yfinance + cache + mock)
│   └── indicators.py        # Vectorized VWAP, ATR, EMA, RSI, Opening Range
├── strategies/
│   ├── base_strategy.py     # Abstract strategy base class
│   └── orb_vwap_strategy.py # 15-min ORB + VWAP + Volume Breakout strategy
├── risk/
│   └── risk_manager.py      # Position sizing, dynamic SL/TP, daily drawdown circuit breaker
├── execution/
│   ├── broker_base.py       # Abstract broker interface
│   ├── paper_broker.py      # Paper trading simulator with slippage & commission fees
│   └── live_broker.py       # Live broker connector (Zerodha Kite, Angel One, Alpaca)
├── engine/
│   ├── scheduler.py         # Market hours and session timer
│   └── trading_engine.py    # Main orchestration loop connecting all components
├── backtest/
│   └── backtester.py        # Event-driven backtesting engine with performance tables
├── ui/
│   └── terminal_ui.py       # Live Rich terminal monitoring dashboard
├── tests/
│   ├── test_indicators.py   # Unit tests for VWAP, ATR, EMA, ORB
│   ├── test_risk_manager.py # Unit tests for position sizing and circuit breaker
│   └── test_strategy.py     # Unit tests for signal generation and exits
├── requirements.txt         # Project dependencies
├── main.py                  # CLI entry point
└── README.md                # Documentation
```

---

## 🚀 Quickstart Guide

### 1. Run Unit Tests
Verify all technical indicators, risk calculations, and strategy logic:
```bash
python -m pytest tests/ -v
```

### 2. Live Market Scanner
Perform a one-shot technical scan across your watchlist:
```bash
python main.py --mode scan
```

### 3. Historical Backtest
Evaluate the bot across recent market days with comprehensive performance statistics:
```bash
python main.py --mode backtest --symbols RELIANCE.NS,TCS.NS,INFY.NS --days 5
```

### 4. Fast-Forward Day Simulation
Simulate a complete intraday trading day (09:15 to 15:30) in seconds:
```bash
python main.py --mode simulate-day
```

### 5. Live Paper Trading Mode
Launch the real-time bot with live dashboard:
```bash
python main.py --mode paper
```

---

## ⚙️ Configuration Reference (`config/config.yaml`)

```yaml
account:
  initial_capital: 50000.0   # Account capital in INR or USD
  currency: "INR"

risk_management:
  risk_per_trade_percent: 1.0     # 1% capital risk per trade
  max_daily_loss_percent: 3.0     # 3% daily circuit breaker
  max_open_positions: 3           # Max concurrent positions
  reward_to_risk_ratio: 2.0       # Minimum 1:2 R:R
  use_trailing_stop: true
  breakeven_trigger_r: 1.0        # Move SL to BE at +1R profit
  trail_step_atr: 1.0             # ATR trailing step

market:
  name: "NSE"
  timezone: "Asia/Kolkata"
  session_open: "09:15"
  entry_start: "09:30"            # Earliest entry after 15m ORB
  entry_cutoff: "11:30"           # No new entries after 11:30
  square_off_time: "15:15"        # Auto square-off before market close
  session_close: "15:30"
```

---

## 🔌 Connecting to Live Brokers

When ready to switch from Paper Trading to a live broker:
1. Update `config/config.yaml`:
   ```yaml
   execution:
     mode: "live"
     broker_type: "zerodha" # or "angelone", "alpaca"
   ```
2. Set your environment variables in your terminal:
   ```bash
   $env:BROKER_API_KEY="your_api_key"
   $env:BROKER_API_SECRET="your_api_secret"
   $env:BROKER_ACCESS_TOKEN="your_access_token"
   ```
3. The adapter in `execution/live_broker.py` routes orders as `MIS` (Margin Intraday Square-off) with your broker.
