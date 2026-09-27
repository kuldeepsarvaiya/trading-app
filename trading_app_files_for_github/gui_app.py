"""Modern Windows Desktop GUI Application for the Intraday Algo Trading Bot with 360° Confluence Engine."""

import sys
import os
import time
import threading
import queue
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config_loader import Config
from core.models import Order, OrderAction, OrderType, Signal, SignalType, Position, TradeRecord
from execution.paper_broker import PaperBroker
from risk.risk_manager import RiskManager
from strategies.confluence_strategy import ConfluenceStrategy
from strategies.trend_analyzer import MarketTrendAnalyzer
from data.news_sentiment import NewsSentimentAnalyzer
from data.dynamic_screener import DynamicMomentumScreener
from data.data_feed import DataFeed
from engine.scheduler import MarketScheduler
from engine.trading_engine import TradingEngine


class AlgoBotGUI:
    """Desktop Window Application for the Intraday Algo Trading Bot."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("⚡ Intraday Algo Trading Bot - 360° Confluence Desktop Edition")
        self.root.geometry("1240x820")
        self.root.minsize(1050, 700)

        # Configuration & Backend Engines
        self.config = Config.load()
        self.broker = PaperBroker(self.config)
        self.risk_manager = RiskManager(self.config)
        self.strategy = ConfluenceStrategy(self.config)
        self.trend_analyzer = MarketTrendAnalyzer()
        self.news_analyzer = NewsSentimentAnalyzer()
        self.data_feed = DataFeed()
        self.screener = DynamicMomentumScreener(self.data_feed)
        self.scheduler = MarketScheduler(self.config)
        self.engine = TradingEngine(self.config, broker=self.broker)

        # State management
        self.is_running = False
        self.bot_thread = None
        self.log_queue = queue.Queue()

        # Modern Dark Color Palette
        self.colors = {
            "bg": "#181825",
            "card_bg": "#1e1e2e",
            "card_header": "#313244",
            "text": "#cdd6f4",
            "text_muted": "#a6adc8",
            "text_bright": "#ffffff",
            "green": "#a6e3a1",
            "green_btn": "#2e7d32",
            "red": "#f38ba8",
            "red_btn": "#c62828",
            "blue": "#89b4fa",
            "blue_btn": "#1565c0",
            "orange_btn": "#e65100",
            "purple_btn": "#6a1b9a",
            "yellow": "#f9e2af",
            "border": "#45475a",
        }

        self.root.configure(bg=self.colors["bg"])
        self._setup_styles()
        self._build_ui()

        # Start periodic GUI updates and log consumer
        self._poll_logs()
        self._update_clock()
        self._update_market_index_badge()

    def _setup_styles(self):
        """Configure ttk styles for dark theme."""
        style = ttk.Style()
        style.theme_use("clam")

        # Tabs Style
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.colors["card_header"],
            foreground=self.colors["text"],
            padding=[14, 8],
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.colors["blue_btn"])],
            foreground=[("selected", "#ffffff")],
        )

        # Treeview (Tables) Style
        style.configure(
            "Treeview",
            background=self.colors["card_bg"],
            foreground=self.colors["text"],
            fieldbackground=self.colors["card_bg"],
            font=("Consolas", 10),
            rowheight=28,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["card_header"],
            foreground=self.colors["text_bright"],
            font=("Segoe UI", 10, "bold"),
            borderwidth=1,
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#45475a")])

    def _build_ui(self):
        """Builds all panels of the software window."""
        self._build_header()
        self._build_metric_cards()
        self._build_controls_bar()
        self._build_tabs()
        self._build_logs_panel()

    def _build_header(self):
        """Header with App Title, Nifty 50 Index Trend, Clock, and Bot Status."""
        header_frame = tk.Frame(self.root, bg=self.colors["card_bg"], height=55, padx=15, pady=8)
        header_frame.pack(fill=tk.X, padx=12, pady=(10, 5))

        title_label = tk.Label(
            header_frame,
            text="⚡ INTRADAY ALGO BOT - 360° CONFLUENCE EDITION",
            font=("Segoe UI", 13, "bold"),
            fg=self.colors["blue"],
            bg=self.colors["card_bg"],
        )
        title_label.pack(side=tk.LEFT)

        # Right-side indicators
        self.lbl_clock = tk.Label(
            header_frame,
            text="🕒 00:00:00",
            font=("Consolas", 11, "bold"),
            fg=self.colors["yellow"],
            bg=self.colors["card_bg"],
        )
        self.lbl_clock.pack(side=tk.RIGHT, padx=10)

        # Live Market Index Trend Gauge
        self.lbl_index_status = tk.Label(
            header_frame,
            text="NIFTY 50: Loading...",
            font=("Segoe UI", 10, "bold"),
            fg=self.colors["green"],
            bg=self.colors["card_header"],
            padx=10,
            pady=3,
        )
        self.lbl_index_status.pack(side=tk.RIGHT, padx=10)

        self.lbl_bot_state = tk.Label(
            header_frame,
            text="STATUS: STOPPED",
            font=("Segoe UI", 10, "bold"),
            fg=self.colors["red"],
            bg=self.colors["card_header"],
            padx=10,
            pady=3,
        )
        self.lbl_bot_state.pack(side=tk.RIGHT, padx=10)

    def _build_metric_cards(self):
        """Top cards showing live Capital, Cash, P&L, Trades, and Win Rate."""
        cards_frame = tk.Frame(self.root, bg=self.colors["bg"])
        cards_frame.pack(fill=tk.X, padx=12, pady=5)

        def create_card(parent, title, default_val, val_color):
            card = tk.Frame(parent, bg=self.colors["card_bg"], padx=14, pady=10, relief="solid", bd=1)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
            lbl_title = tk.Label(card, text=title, font=("Segoe UI", 9), fg=self.colors["text_muted"], bg=self.colors["card_bg"])
            lbl_title.pack(anchor="w")
            lbl_val = tk.Label(card, text=default_val, font=("Segoe UI", 14, "bold"), fg=val_color, bg=self.colors["card_bg"])
            lbl_val.pack(anchor="w", pady=(4, 0))
            return lbl_val

        self.val_starting_cap = create_card(cards_frame, "Starting Capital", f"{self.config.currency} {self.config.initial_capital:,.2f}", self.colors["text_bright"])
        self.val_cash_balance = create_card(cards_frame, "Available Cash (5x MIS)", f"{self.config.currency} {self.config.initial_capital:,.2f}", self.colors["blue"])
        self.val_portfolio = create_card(cards_frame, "Portfolio Equity", f"{self.config.currency} {self.config.initial_capital:,.2f}", self.colors["yellow"])
        self.val_total_pnl = create_card(cards_frame, "Today's Net P&L", f"{self.config.currency} +0.00 (0.00%)", self.colors["green"])
        self.val_win_rate = create_card(cards_frame, "Win Rate / Trades", "0 Trades (0%)", self.colors["text_bright"])

    def _build_controls_bar(self):
        """Action buttons to control the Bot."""
        bar = tk.Frame(self.root, bg=self.colors["card_bg"], padx=12, pady=8)
        bar.pack(fill=tk.X, padx=12, pady=5)

        # Start Button
        self.btn_start = tk.Button(
            bar,
            text="▶  START ALGO BOT",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["green_btn"],
            fg="#ffffff",
            activebackground="#388e3c",
            relief="flat",
            padx=14,
            pady=6,
            command=self.start_bot,
        )
        self.btn_start.pack(side=tk.LEFT, padx=4)

        # Stop Button
        self.btn_stop = tk.Button(
            bar,
            text="⏹  STOP BOT",
            font=("Segoe UI", 10, "bold"),
            bg="#424242",
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            state=tk.DISABLED,
            command=self.stop_bot,
        )
        self.btn_stop.pack(side=tk.LEFT, padx=4)

        # 360° Scan Now Button
        self.btn_scan = tk.Button(
            bar,
            text="🔍  360° WATCHLIST SCAN",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["blue_btn"],
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=6,
            command=self.manual_scan_threaded,
        )
        self.btn_scan.pack(side=tk.LEFT, padx=4)

        # 10%-15% Dynamic Momentum Runners Screener
        self.btn_runners = tk.Button(
            bar,
            text="🔥  SCREEN 10%-15% RUNNERS",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["purple_btn"],
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=6,
            command=self.scan_runners_threaded,
        )
        self.btn_runners.pack(side=tk.LEFT, padx=4)

        # 3-Second Quick Test Button
        self.btn_test = tk.Button(
            bar,
            text="🧪  3-SEC SIMULATION",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["orange_btn"],
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=6,
            command=self.run_fast_simulation,
        )
        self.btn_test.pack(side=tk.LEFT, padx=4)

        # Emergency Square-Off Button
        self.btn_sq = tk.Button(
            bar,
            text="🚨  SQUARE-OFF ALL",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["red_btn"],
            fg="#ffffff",
            activebackground="#d32f2f",
            relief="flat",
            padx=14,
            pady=6,
            command=self.emergency_square_off,
        )
        self.btn_sq.pack(side=tk.RIGHT, padx=4)

    def _build_tabs(self):
        """Tabs for Active Positions, Watchlist Scanner, Top Runners, Closed Trades, and Settings."""
        notebook_frame = tk.Frame(self.root, bg=self.colors["bg"])
        notebook_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)

        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Active Positions
        self.tab_positions = tk.Frame(self.notebook, bg=self.colors["card_bg"])
        self.notebook.add(self.tab_positions, text="📈  Active Positions (0)")
        self._build_positions_table()

        # Tab 2: 360° Watchlist Scanner
        self.tab_scanner = tk.Frame(self.notebook, bg=self.colors["card_bg"])
        self.notebook.add(self.tab_scanner, text="🔍  360° Watchlist Scanner")
        self._build_scanner_table()

        # Tab 3: Dynamic 10%-15% Momentum Runners
        self.tab_runners = tk.Frame(self.notebook, bg=self.colors["card_bg"])
        self.notebook.add(self.tab_runners, text="🔥  Top 10%-15% Runners")
        self._build_runners_table()

        # Tab 4: Closed Trades Ledger
        self.tab_trades = tk.Frame(self.notebook, bg=self.colors["card_bg"])
        self.notebook.add(self.tab_trades, text="📜  Closed Trades History")
        self._build_trades_table()

        # Tab 5: Settings
        self.tab_settings = tk.Frame(self.notebook, bg=self.colors["card_bg"])
        self.notebook.add(self.tab_settings, text="⚙️  Bot Settings")
        self._build_settings_tab()

    def _build_positions_table(self):
        """Table for active positions."""
        cols = ("symbol", "qty", "entry", "ltp", "stop_loss", "target", "trailing_sl", "pnl", "return")
        self.pos_tree = ttk.Treeview(self.tab_positions, columns=cols, show="headings", selectmode="browse")
        
        headings = {
            "symbol": "Stock Symbol",
            "qty": "Quantity",
            "entry": "Entry Price",
            "ltp": "LTP (Current)",
            "stop_loss": "Initial SL",
            "target": "Target (1:2)",
            "trailing_sl": "Trailing SL",
            "pnl": "Unrealized P&L",
            "return": "Return %",
        }
        for col_id, title in headings.items():
            self.pos_tree.heading(col_id, text=title)
            self.pos_tree.column(col_id, anchor="center", width=110)
        self.pos_tree.column("symbol", anchor="w", width=140)

        sb = ttk.Scrollbar(self.tab_positions, orient=tk.VERTICAL, command=self.pos_tree.yview)
        self.pos_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.pos_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _build_scanner_table(self):
        """Table for 360° live watchlist scanner with news and confluence score."""
        cols = ("symbol", "ltp", "vwap", "ema", "rsi", "vol_surge", "news_catalyst", "confluence", "status")
        self.scan_tree = ttk.Treeview(self.tab_scanner, columns=cols, show="headings", selectmode="browse")

        headings = {
            "symbol": "Symbol",
            "ltp": "LTP",
            "vwap": "VWAP",
            "ema": "EMA 9/21",
            "rsi": "RSI (14)",
            "vol_surge": "Vol Surge",
            "news_catalyst": "News & Sentiment Catalyst",
            "confluence": "Confluence Score",
            "status": "Bot Signal",
        }
        for col_id, title in headings.items():
            self.scan_tree.heading(col_id, text=title)
            self.scan_tree.column(col_id, anchor="center", width=105)
        self.scan_tree.column("symbol", anchor="w", width=125)
        self.scan_tree.column("news_catalyst", anchor="w", width=220)
        self.scan_tree.column("confluence", anchor="center", width=120)

        sb = ttk.Scrollbar(self.tab_scanner, orient=tk.VERTICAL, command=self.scan_tree.yview)
        self.scan_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.scan_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _build_runners_table(self):
        """Table for dynamic 10%-15% momentum runners."""
        cols = ("symbol", "ltp", "day_change", "day_high", "vwap", "vol_surge", "rsi", "momentum_score", "potential")
        self.runners_tree = ttk.Treeview(self.tab_runners, columns=cols, show="headings", selectmode="browse")

        headings = {
            "symbol": "Momentum Stock",
            "ltp": "LTP",
            "day_change": "Day Gain %",
            "day_high": "Day High",
            "vwap": "VWAP",
            "vol_surge": "Vol Surge",
            "rsi": "RSI (14)",
            "momentum_score": "Runner Score",
            "potential": "Breakout Potential",
        }
        for col_id, title in headings.items():
            self.runners_tree.heading(col_id, text=title)
            self.runners_tree.column(col_id, anchor="center", width=115)
        self.runners_tree.column("symbol", anchor="w", width=130)

        sb = ttk.Scrollbar(self.tab_runners, orient=tk.VERTICAL, command=self.runners_tree.yview)
        self.runners_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.runners_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _build_trades_table(self):
        """Table for completed trades ledger."""
        cols = ("symbol", "qty", "entry", "exit", "gross_pnl", "fees", "net_pnl", "return", "reason")
        self.trades_tree = ttk.Treeview(self.tab_trades, columns=cols, show="headings", selectmode="browse")

        headings = {
            "symbol": "Symbol",
            "qty": "Qty",
            "entry": "Entry Price",
            "exit": "Exit Price",
            "gross_pnl": "Gross P&L",
            "fees": "Brokerage & Taxes",
            "net_pnl": "Net P&L",
            "return": "Return %",
            "reason": "Exit Reason",
        }
        for col_id, title in headings.items():
            self.trades_tree.heading(col_id, text=title)
            self.trades_tree.column(col_id, anchor="center", width=110)
        self.trades_tree.column("symbol", anchor="w", width=130)
        self.trades_tree.column("reason", anchor="w", width=220)

        sb = ttk.Scrollbar(self.tab_trades, orient=tk.VERTICAL, command=self.trades_tree.yview)
        self.trades_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.trades_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _build_settings_tab(self):
        """Settings tab for adjusting parameters."""
        p = tk.Frame(self.tab_settings, bg=self.colors["card_bg"], padx=20, pady=20)
        p.pack(fill=tk.BOTH, expand=True)

        tk.Label(p, text="⚙️ Bot Trading & Risk Parameters", font=("Segoe UI", 12, "bold"), fg=self.colors["text_bright"], bg=self.colors["card_bg"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        tk.Label(p, text="Initial Capital (INR):", font=("Segoe UI", 10), fg=self.colors["text"], bg=self.colors["card_bg"]).grid(row=1, column=0, sticky="w", pady=6)
        self.ent_capital = tk.Entry(p, font=("Consolas", 10), width=25, bg="#2a2b3d", fg="#ffffff", insertbackground="#ffffff")
        self.ent_capital.insert(0, str(self.config.initial_capital))
        self.ent_capital.grid(row=1, column=1, sticky="w", pady=6)

        tk.Label(p, text="Risk Per Trade (%):", font=("Segoe UI", 10), fg=self.colors["text"], bg=self.colors["card_bg"]).grid(row=2, column=0, sticky="w", pady=6)
        self.ent_risk = tk.Entry(p, font=("Consolas", 10), width=25, bg="#2a2b3d", fg="#ffffff", insertbackground="#ffffff")
        self.ent_risk.insert(0, str(self.config.risk_per_trade_percent))
        self.ent_risk.grid(row=2, column=1, sticky="w", pady=6)

        tk.Label(p, text="Daily Circuit Breaker (%):", font=("Segoe UI", 10), fg=self.colors["text"], bg=self.colors["card_bg"]).grid(row=3, column=0, sticky="w", pady=6)
        self.ent_loss = tk.Entry(p, font=("Consolas", 10), width=25, bg="#2a2b3d", fg="#ffffff", insertbackground="#ffffff")
        self.ent_loss.insert(0, str(self.config.max_daily_loss_percent))
        self.ent_loss.grid(row=3, column=1, sticky="w", pady=6)

        tk.Label(p, text="Min Confluence Score (Out of 100):", font=("Segoe UI", 10), fg=self.colors["text"], bg=self.colors["card_bg"]).grid(row=4, column=0, sticky="w", pady=6)
        self.ent_score = tk.Entry(p, font=("Consolas", 10), width=25, bg="#2a2b3d", fg="#ffffff", insertbackground="#ffffff")
        self.ent_score.insert(0, "75")
        self.ent_score.grid(row=4, column=1, sticky="w", pady=6)

        tk.Label(p, text="Auto Square-Off Time (HH:MM):", font=("Segoe UI", 10), fg=self.colors["text"], bg=self.colors["card_bg"]).grid(row=5, column=0, sticky="w", pady=6)
        self.ent_sq_time = tk.Entry(p, font=("Consolas", 10), width=25, bg="#2a2b3d", fg="#ffffff", insertbackground="#ffffff")
        self.ent_sq_time.insert(0, str(self.config.square_off_time))
        self.ent_sq_time.grid(row=5, column=1, sticky="w", pady=6)

        btn_save = tk.Button(
            p,
            text="💾  SAVE SETTINGS",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["blue_btn"],
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            command=self._save_settings,
        )
        btn_save.grid(row=6, column=1, sticky="w", pady=15)

    def _build_logs_panel(self):
        """Bottom console for real-time audit logs."""
        log_frame = tk.Frame(self.root, bg=self.colors["card_bg"], height=160, padx=12, pady=6)
        log_frame.pack(fill=tk.X, padx=12, pady=(0, 10))

        lbl = tk.Label(log_frame, text="📋 Real-Time Activity & Trade Audit Log", font=("Segoe UI", 9, "bold"), fg=self.colors["text_muted"], bg=self.colors["card_bg"])
        lbl.pack(anchor="w")

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=6,
            font=("Consolas", 9),
            bg="#11111b",
            fg=self.colors["text"],
            insertbackground="#ffffff",
            relief="flat",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.log_message("🚀 360° Confluence Algo Bot Desktop Software initialized and ready.")

    def log_message(self, msg: str):
        """Thread-safe logging helper."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {msg}")

    def _poll_logs(self):
        """Pulls messages from queue and appends to text widget."""
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
        self.root.after(200, self._poll_logs)

    def _update_clock(self):
        """Live clock update every second."""
        now_str = datetime.now().strftime("🕒 %H:%M:%S")
        self.lbl_clock.config(text=now_str)
        self.root.after(1000, self._update_clock)

    def _update_market_index_badge(self):
        """Updates NIFTY 50 live status every 60 seconds."""
        def fetch():
            try:
                res = self.trend_analyzer.get_market_index_status()
                color = self.colors["green"] if res.get("is_safe_to_buy") else self.colors["red"]
                self.root.after(0, lambda: self.lbl_index_status.config(text=res.get("label", "NIFTY 50: Active"), fg=color))
            except Exception:
                pass
        threading.Thread(target=fetch, daemon=True).start()
        self.root.after(60000, self._update_market_index_badge)

    def start_bot(self):
        """Starts live trading engine in background thread."""
        if self.is_running:
            return

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED, bg="#424242")
        self.btn_stop.config(state=tk.NORMAL, bg=self.colors["red_btn"])
        self.lbl_bot_state.config(text="STATUS: RUNNING", fg=self.colors["green"])
        self.log_message("🟢 360° Confluence Algo Bot STARTED! Scanning market with News & Trend analysis...")

        self.bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
        self.bot_thread.start()

    def stop_bot(self):
        """Stops live trading engine loop."""
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL, bg=self.colors["green_btn"])
        self.btn_stop.config(state=tk.DISABLED, bg="#424242")
        self.lbl_bot_state.config(text="STATUS: STOPPED", fg=self.colors["red"])
        self.log_message("⏹ Algo Bot STOPPED.")

    def _bot_loop(self):
        """Continuous background execution loop."""
        while self.is_running:
            try:
                res = self.engine.step()
                self.root.after(0, self._refresh_tables)
                if res.get("signals"):
                    for sig in res["signals"]:
                        self.log_message(f"🎯 Buy Signal: {sig.symbol} @ {sig.price:.2f} ({sig.reason})")
                if res.get("closed_trades"):
                    for t in res["closed_trades"]:
                        self.log_message(f"✅ Closed: {t.symbol} | Net P&L: {t.net_pnl:+.2f} ({t.exit_reason})")
            except Exception as e:
                self.log_message(f"⚠️ Engine Step Error: {e}")

            for _ in range(15):
                if not self.is_running:
                    break
                time.sleep(1)

    def manual_scan_threaded(self):
        """Runs one-shot 360° market scan in a thread to keep GUI responsive."""
        self.log_message("🔍 Starting 360° Watchlist Scan with News Sentiment & Confluence...")
        threading.Thread(target=self._manual_scan_worker, daemon=True).start()

    def _manual_scan_worker(self):
        try:
            for item in self.scan_tree.get_children():
                self.root.after(0, self.scan_tree.delete, item)

            for sym in self.config.symbols:
                df = self.data_feed.fetch_intraday_history(sym, interval=self.config.timeframe, days=1, use_cache=True)
                if df.empty:
                    self.root.after(0, self.scan_tree.insert, "", tk.END, values=(sym, "N/A", "-", "-", "-", "-", "No News", "-", "Idle"))
                    continue

                candle = df.iloc[-1]
                close = float(candle["close"])
                vwap = float(candle.get("vwap", close))
                ema9 = float(candle.get("ema_fast", close))
                ema21 = float(candle.get("ema_slow", close))
                rsi = float(candle.get("rsi", 50.0))
                vol_surge = float(candle.get("vol_surge", 1.0))

                # Analyze News & Sentiment
                news_res = self.news_analyzer.analyze_symbol_news(sym)
                catalyst_tag = news_res.get("catalyst_tag", "⚪ Neutral")

                # Confluence Score calculation
                tech_pts = 20 if (close > vwap and ema9 > ema21) else 10
                vol_pts = 25 if vol_surge >= 1.8 else (15 if vol_surge >= 1.2 else 5)
                news_pts = news_res.get("points", 10)
                confluence_score = tech_pts + vol_pts + 15 + news_pts  # out of 100

                status = "HOLDING" if sym in self.broker.get_open_positions() else ("BUY CANDIDATE ⭐" if confluence_score >= 75 else "MONITORING")
                ema_str = f"{ema9:.1f}/{ema21:.1f}"

                row_vals = (sym, f"{close:.2f}", f"{vwap:.2f}", ema_str, f"{rsi:.1f}", f"{vol_surge:.2f}x", catalyst_tag, f"{confluence_score}/100", status)
                self.root.after(0, self.scan_tree.insert, "", tk.END, values=row_vals)

            self.log_message("✅ 360° Watchlist Scan completed.")
        except Exception as e:
            self.log_message(f"⚠️ Scan error: {e}")

    def scan_runners_threaded(self):
        """Scans dynamic momentum universe for 10%-15% runners."""
        self.log_message("🔥 Scanning High-Beta Universe for 10%-15% Momentum Runners...")
        self.notebook.select(self.tab_runners)
        threading.Thread(target=self._runners_worker, daemon=True).start()

    def _runners_worker(self):
        try:
            runners = self.screener.scan_top_runners(top_n=10)
            for item in self.runners_tree.get_children():
                self.root.after(0, self.runners_tree.delete, item)

            for r in runners:
                gain_str = f"{r['day_change_pct']:+.2f}%"
                potential = "🚀 HIGH BREAKOUT" if r['is_runner_candidate'] else "MONITORING"
                row = (
                    r["symbol"],
                    f"{r['ltp']:.2f}",
                    gain_str,
                    f"{r['day_high']:.2f}",
                    f"{r['vwap']:.2f}",
                    f"{r['vol_surge']:.2f}x",
                    f"{r['rsi']:.1f}",
                    f"{r['momentum_score']}/100",
                    potential
                )
                self.root.after(0, self.runners_tree.insert, "", tk.END, values=row)

            self.log_message(f"🎉 Identified {len(runners)} Top Momentum Runners!")
        except Exception as e:
            self.log_message(f"⚠️ Runners screener error: {e}")

    def emergency_square_off(self):
        """Immediately closes all open positions."""
        positions = self.broker.get_open_positions()
        if not positions:
            messagebox.showinfo("Square-Off", "No open positions to close.")
            return

        confirm = messagebox.askyesno(
            "🚨 Emergency Square-Off",
            f"Are you sure you want to CLOSE ALL {len(positions)} active positions right now?"
        )
        if confirm:
            trades = self.broker.square_off_all_positions({}, reason="User Emergency Square-Off")
            for t in trades:
                self.risk_manager.update_realized_pnl(t.net_pnl)
                self.log_message(f"🚨 CLOSED {t.symbol} @ {t.exit_price:.2f} | P&L: {t.net_pnl:+.2f}")
            self._refresh_tables()
            messagebox.showinfo("Square-Off Complete", f"Successfully closed {len(trades)} positions.")

    def run_fast_simulation(self):
        """Runs 3-second simulation and loads trades into GUI."""
        self.log_message("🎬 Running 3-second testing simulation...")
        
        sig_infy = Signal("INFY.NS", SignalType.BUY, datetime.now(), 1000.0, 990.0, 1020.0, "[Confluence: 88/100 ⭐] ORB Breakout + Earnings Beat (+90%)")
        _, qty1, _ = self.risk_manager.validate_and_size_order(sig_infy, 0)
        self.broker.execute_order(Order("ord_sim_1", "INFY.NS", OrderAction.BUY, qty1, OrderType.MARKET, 1000.0))
        
        sig_rel = Signal("RELIANCE.NS", SignalType.BUY, datetime.now(), 1250.0, 1238.0, 1274.0, "[Confluence: 82/100 ⭐] ORB Breakout + Order Win (+85%)")
        _, qty2, _ = self.risk_manager.validate_and_size_order(sig_rel, 1)
        self.broker.execute_order(Order("ord_sim_2", "RELIANCE.NS", OrderAction.BUY, qty2, OrderType.MARKET, 1250.0))

        self.broker.close_position("INFY.NS", 1020.0, "Take-Profit Target Hit (1:2)")
        self.broker.close_position("RELIANCE.NS", 1262.0, "Mandatory 15:15 Auto Square-Off")

        self._refresh_tables()
        self.log_message("🎉 3-Second Simulation complete! Trades with Confluence scores loaded into GUI.")

    def _refresh_tables(self):
        """Refreshes all treeviews and top metric cards."""
        cash = self.broker.get_cash_balance()
        portfolio = self.broker.get_portfolio_value()
        realized_pnl = self.risk_manager.realized_pnl_today
        positions = self.broker.get_open_positions()
        unrealized_pnl = sum(p.unrealized_pnl for p in positions.values())
        total_pnl = realized_pnl + unrealized_pnl
        roi_pct = ((portfolio - self.config.initial_capital) / self.config.initial_capital) * 100.0

        pnl_color = self.colors["green"] if total_pnl >= 0 else self.colors["red"]
        self.val_cash_balance.config(text=f"{self.config.currency} {cash:,.2f}")
        self.val_portfolio.config(text=f"{self.config.currency} {portfolio:,.2f}")
        self.val_total_pnl.config(text=f"{self.config.currency} {total_pnl:+,.2f} ({roi_pct:+.2f}%)", fg=pnl_color)

        history = self.broker.get_trade_history()
        wins = sum(1 for t in history if t.net_pnl > 0)
        win_rate = (wins / len(history) * 100.0) if history else 0.0
        self.val_win_rate.config(text=f"{len(history)} Trades ({win_rate:.0f}% Wins)")

        self.notebook.tab(0, text=f"📈  Active Positions ({len(positions)})")
        for item in self.pos_tree.get_children():
            self.pos_tree.delete(item)

        for p in positions.values():
            self.pos_tree.insert(
                "",
                tk.END,
                values=(
                    p.symbol,
                    p.quantity,
                    f"{p.entry_price:.2f}",
                    f"{p.current_price:.2f}",
                    f"{p.stop_loss:.2f}",
                    f"{p.target:.2f}",
                    f"{p.trailing_sl:.2f}",
                    f"{p.unrealized_pnl:+.2f}",
                    f"{p.unrealized_pnl_percent:+.2f}%",
                )
            )

        for item in self.trades_tree.get_children():
            self.trades_tree.delete(item)

        for t in reversed(history):
            self.trades_tree.insert(
                "",
                tk.END,
                values=(
                    t.symbol,
                    t.quantity,
                    f"{t.entry_price:.2f}",
                    f"{t.exit_price:.2f}",
                    f"{t.gross_pnl:+.2f}",
                    f"{t.commission:.2f}",
                    f"{t.net_pnl:+.2f}",
                    f"{t.return_pct:+.2f}%",
                    t.exit_reason,
                )
            )

    def _save_settings(self):
        """Saves updated settings from UI."""
        try:
            self.config.raw["account"]["initial_capital"] = float(self.ent_capital.get())
            self.config.raw["risk_management"]["risk_per_trade_percent"] = float(self.ent_risk.get())
            self.config.raw["risk_management"]["max_daily_loss_percent"] = float(self.ent_loss.get())
            self.config.raw["market"]["square_off_time"] = self.ent_sq_time.get()
            self.strategy.min_confluence_score = int(self.ent_score.get())
            self.log_message(f"💾 Settings updated. Min Confluence Score: {self.strategy.min_confluence_score}/100.")
            messagebox.showinfo("Settings", "Bot settings updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")


def main():
    root = tk.Tk()
    app = AlgoBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
