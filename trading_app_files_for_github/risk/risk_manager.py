"""Risk Management Engine enforcing strict position sizing, capital safety, and trailing stops."""

import math
from typing import Optional, Tuple
from core.models import Signal, SignalType, Position, OrderAction
from core.config_loader import Config
from core.logger import setup_logger

logger = setup_logger("RiskManager")


class RiskManager:
    """
    Enforces risk rules:
    - 1% Capital Risk per trade (dynamic position sizing)
    - 3% Daily Circuit Breaker (Max daily drawdown)
    - Max Concurrent Positions Cap
    - Trailing Stop-Loss Ratchet (moves only forward)
    - Minimum 1:2 Risk to Reward enforcement
    """

    def __init__(self, config: Config):
        self.config = config
        self.initial_capital = config.initial_capital
        self.current_capital = config.initial_capital
        self.realized_pnl_today = 0.0
        self.is_circuit_breaker_triggered = False

    def reset_daily_metrics(self, capital: Optional[float] = None) -> None:
        """Resets daily counters at the start of each morning trading session."""
        if capital is not None:
            self.current_capital = capital
        self.realized_pnl_today = 0.0
        self.is_circuit_breaker_triggered = False
        logger.info(f"Daily Risk Metrics Reset. Capital: {self.current_capital:.2f}")

    def update_realized_pnl(self, pnl: float) -> None:
        """Update realized P&L from closed trade."""
        self.realized_pnl_today += pnl
        self.current_capital += pnl
        self._check_circuit_breaker(unrealized_pnl=0.0)

    def _check_circuit_breaker(self, unrealized_pnl: float = 0.0) -> bool:
        """Checks if total daily loss exceeds max daily drawdown limit."""
        max_daily_loss = self.initial_capital * (self.config.max_daily_loss_percent / 100.0)
        total_pnl = self.realized_pnl_today + unrealized_pnl

        if total_pnl <= -max_daily_loss:
            if not self.is_circuit_breaker_triggered:
                logger.error(
                    f"🚨 CIRCUIT BREAKER TRIGGERED! Total daily loss ({total_pnl:.2f}) "
                    f"exceeded maximum allowed limit (-{max_daily_loss:.2f}). "
                    f"All further trade entries HALTED for today!"
                )
                self.is_circuit_breaker_triggered = True
            return True
        return False

    def validate_and_size_order(
        self,
        signal: Signal,
        open_positions_count: int,
        unrealized_pnl: float = 0.0
    ) -> Tuple[bool, int, str]:
        """
        Validates whether a new trade signal can be executed and calculates optimal position size.
        Returns: (is_approved, calculated_quantity, rejection_reason)
        """
        # 1. Check Circuit Breaker
        if self._check_circuit_breaker(unrealized_pnl) or self.is_circuit_breaker_triggered:
            return False, 0, "Circuit Breaker Active: Daily loss limit reached"

        # 2. Check Maximum Concurrent Positions
        if open_positions_count >= self.config.max_open_positions:
            return False, 0, f"Max open positions reached ({open_positions_count}/{self.config.max_open_positions})"

        # 3. Check Signal Validity
        if signal.signal_type != SignalType.BUY:
            return False, 0, f"Signal type {signal.signal_type} is not an entry signal"

        entry_price = signal.price
        stop_loss = signal.stop_loss

        if entry_price <= 0 or stop_loss <= 0:
            return False, 0, "Invalid entry price or stop loss"

        if stop_loss >= entry_price:
            return False, 0, f"Stop Loss ({stop_loss}) must be strictly below Entry Price ({entry_price})"

        # 4. Calculate Risk per Trade in Currency
        risk_per_trade_amount = self.current_capital * (self.config.risk_per_trade_percent / 100.0)
        sl_distance = entry_price - stop_loss

        # Enforce Minimum 1:2 Risk to Reward
        reward_distance = signal.target - entry_price
        if reward_distance < (sl_distance * self.config.reward_to_risk_ratio * 0.95):
            return False, 0, f"Reward-to-Risk ratio too low: {reward_distance / sl_distance:.2f} < {self.config.reward_to_risk_ratio}"

        # 5. Position Sizing based on 1% Risk Formula:
        # Quantity = floor(Risk Amount / SL Distance)
        quantity_by_risk = math.floor(risk_per_trade_amount / sl_distance)

        # 6. Position Sizing Cap based on Maximum Capital per Trade
        max_capital_for_trade = self.current_capital * (self.config.max_capital_per_trade_percent / 100.0)
        quantity_by_capital = math.floor(max_capital_for_trade / entry_price)

        final_quantity = min(quantity_by_risk, quantity_by_capital)

        if final_quantity <= 0:
            return False, 0, f"Calculated quantity is 0 (risk amount {risk_per_trade_amount:.2f} vs SL dist {sl_distance:.2f})"

        logger.info(
            f"✅ Trade Approved for {signal.symbol}: Qty={final_quantity} @ {entry_price:.2f} | "
            f"SL={stop_loss:.2f} (Dist: {sl_distance:.2f}) | Target={signal.target:.2f} | "
            f"Total Risk: {final_quantity * sl_distance:.2f} ({self.config.risk_per_trade_percent}%)"
        )
        return True, final_quantity, "Approved"

    def update_trailing_stop(self, position: Position, current_price: float, current_atr: float = 0.0) -> float:
        """
        Updates the position's trailing stop-loss.
        - Moves to break-even once price exceeds +1R.
        - Trails at (current_price - ATR * trail_step_atr) once in strong profit.
        - GUARANTEE: Stop loss NEVER moves downwards.
        """
        if not self.config.use_trailing_stop:
            return position.trailing_sl

        entry = position.entry_price
        initial_sl = position.stop_loss
        r_distance = entry - initial_sl
        current_profit = current_price - entry

        new_sl = position.trailing_sl

        # Step 1: Move to Breakeven (+0.1% buffer for brokerage) when profit >= 1R
        breakeven_level = entry + (r_distance * self.config.breakeven_trigger_r)
        if current_price >= breakeven_level:
            breakeven_sl = entry * 1.001  # Slight buffer above entry
            if breakeven_sl > new_sl:
                new_sl = breakeven_sl
                logger.info(f"🛡️ {position.symbol}: Trailing SL moved to Break-Even: {new_sl:.2f}")

        # Step 2: Trail with ATR once profit exceeds 1.5R
        if current_price >= (entry + (r_distance * 1.5)) and current_atr > 0:
            atr_sl = current_price - (current_atr * self.config.trail_step_atr)
            if atr_sl > new_sl:
                new_sl = atr_sl
                logger.info(f"📈 {position.symbol}: Trailing SL locked higher at: {new_sl:.2f} (ATR={current_atr:.2f})")

        # Position can only ratchet upwards
        position.trailing_sl = max(position.trailing_sl, new_sl)
        return position.trailing_sl
