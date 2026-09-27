"""Opening Range Breakout (ORB) + VWAP + Volume Surge Intraday Strategy."""

from datetime import datetime
from typing import Optional, Tuple
import pandas as pd
from core.models import Signal, SignalType, Position
from core.config_loader import Config
from core.logger import setup_logger
from data.indicators import calculate_opening_range
from strategies.base_strategy import BaseStrategy

logger = setup_logger("ORBVWAPStrategy")


class ORBVWAPStrategy(BaseStrategy):
    """
    Intraday Buy Strategy:
    1. Determines 15-min Opening Range (09:15 - 09:30).
    2. Triggers BUY on 5-min candle when:
       - Close > Opening Range High (Breakout)
       - Close > Intraday VWAP (Bullish institutional bias)
       - EMA 9 > EMA 21 (Bullish trend alignment)
       - Volume >= 1.3x 20-MA volume (Institutional volume expansion)
       - 52 <= RSI <= 75 (Healthy upward momentum)
       - Current time between 09:30 and 11:30 (Prime entry window)
    3. Exits on:
       - Target Hit (1:2 Risk to Reward)
       - Stop Loss or Trailing Stop Loss Hit
       - Mandatory Auto Square-Off at 15:15
    """

    def __init__(self, config: Config):
        super().__init__(name="ORB_VWAP_Momentum")
        self.config = config

    def evaluate_entry(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """Evaluates entry criteria on enriched intraday dataframe."""
        if df.empty or len(df) < 5:
            return None

        latest_candle = df.iloc[-1]
        candle_time = latest_candle.name if isinstance(latest_candle.name, datetime) else df.index[-1]
        time_str = candle_time.strftime("%H:%M")

        # 1. Enforce Trading Window (e.g. 09:30 to 11:30)
        if time_str < self.config.entry_start or time_str > self.config.entry_cutoff:
            return None

        # 2. Calculate Opening Range High and Low
        or_high, or_low = calculate_opening_range(
            df,
            start_time_str=self.config.session_open,
            end_time_str=self.config.entry_start
        )

        if or_high is None or or_low is None:
            return None

        close = float(latest_candle["close"])
        open_price = float(latest_candle["open"])
        high = float(latest_candle["high"])
        low = float(latest_candle["low"])
        vwap = float(latest_candle.get("vwap", 0.0))
        ema_fast = float(latest_candle.get("ema_fast", 0.0))
        ema_slow = float(latest_candle.get("ema_slow", 0.0))
        rsi = float(latest_candle.get("rsi", 50.0))
        atr = float(latest_candle.get("atr", close * 0.01))
        vol_surge = float(latest_candle.get("vol_surge", 1.0))

        # 3. Check Bullish Breakout Rules
        is_breakout = close > or_high and open_price <= or_high * 1.002
        is_above_vwap = close > vwap
        is_ema_bullish = ema_fast > ema_slow
        is_volume_confirmed = vol_surge >= self.config.volume_surge_multiplier
        is_rsi_valid = self.config.rsi_min <= rsi <= self.config.rsi_max

        if is_breakout and is_above_vwap and is_ema_bullish and is_volume_confirmed and is_rsi_valid:
            # Dynamic Stop Loss: Lowest of (Breakout Candle Low, Entry - ATR * multiplier)
            atr_sl = close - (atr * self.config.atr_sl_multiplier)
            candle_sl = low - (atr * 0.2)
            stop_loss = round(max(atr_sl, candle_sl), 2)

            # Ensure Stop Loss is strictly below entry price
            if stop_loss >= close:
                stop_loss = round(close - (atr * self.config.atr_sl_multiplier), 2)

            # Target: 1:2 Risk to Reward
            risk_dist = close - stop_loss
            target = round(close + (risk_dist * self.config.reward_to_risk_ratio), 2)

            reason = (
                f"ORB High ({or_high:.2f}) breakout | Close: {close:.2f} > VWAP ({vwap:.2f}) | "
                f"EMA 9 ({ema_fast:.2f}) > 21 ({ema_slow:.2f}) | Vol Surge: {vol_surge:.2f}x | RSI: {rsi:.1f}"
            )

            signal = Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                timestamp=candle_time,
                price=close,
                stop_loss=stop_loss,
                target=target,
                reason=reason,
                indicators={
                    "or_high": or_high,
                    "or_low": or_low,
                    "vwap": vwap,
                    "ema_fast": ema_fast,
                    "ema_slow": ema_slow,
                    "rsi": rsi,
                    "atr": atr,
                    "vol_surge": vol_surge
                }
            )
            return signal

        return None

    def evaluate_exit(self, position: Position, current_candle: pd.Series, current_time_str: str) -> Optional[Signal]:
        """Checks exit conditions against high, low, close and square-off time."""
        high = float(current_candle["high"])
        low = float(current_candle["low"])
        close = float(current_candle["close"])
        candle_time = current_candle.name if isinstance(current_candle.name, datetime) else datetime.now()

        # 1. Mandatory Auto Square-Off Check (e.g. 15:15)
        if current_time_str >= self.config.square_off_time:
            return Signal(
                symbol=position.symbol,
                signal_type=SignalType.EXIT_SQUAREOFF,
                timestamp=candle_time,
                price=close,
                stop_loss=position.trailing_sl,
                target=position.target,
                reason=f"Mandatory Intraday Square-off at {current_time_str}"
            )

        # 2. Target Hit Check
        if high >= position.target:
            return Signal(
                symbol=position.symbol,
                signal_type=SignalType.EXIT_TARGET,
                timestamp=candle_time,
                price=position.target,
                stop_loss=position.trailing_sl,
                target=position.target,
                reason=f"Take-Profit Target ({position.target:.2f}) Reached!"
            )

        # 3. Trailing Stop Loss / Stop Loss Hit Check
        if low <= position.trailing_sl:
            exit_type = SignalType.EXIT_TRAILING_SL if position.trailing_sl > position.stop_loss else SignalType.EXIT_SL
            return Signal(
                symbol=position.symbol,
                signal_type=exit_type,
                timestamp=candle_time,
                price=position.trailing_sl,
                stop_loss=position.trailing_sl,
                target=position.target,
                reason=f"Stop-Loss triggered at {position.trailing_sl:.2f} (Low: {low:.2f})"
            )

        return None
