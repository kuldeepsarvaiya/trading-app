"""Market schedule tracker and trading lifecycle timer."""

from datetime import datetime, time
import pytz
from core.config_loader import Config
from core.logger import setup_logger

logger = setup_logger("Scheduler")


class MarketScheduler:
    """Tracks market hours, entry windows, and auto square-off times."""

    def __init__(self, config: Config):
        self.config = config
        self.tz = pytz.timezone(config.timezone)

    def get_current_market_time(self) -> datetime:
        """Returns current time localized to market timezone."""
        return datetime.now(self.tz)

    def get_current_time_str(self) -> str:
        return self.get_current_market_time().strftime("%H:%M")

    def is_market_open(self, current_time_str: str = None) -> bool:
        """Checks if current time is between market open and close."""
        t = current_time_str or self.get_current_time_str()
        # Check weekday (0=Mon, 4=Fri, 5=Sat, 6=Sun)
        weekday = self.get_current_market_time().weekday()
        if weekday >= 5:
            return False
        return self.config.session_open <= t <= self.config.session_close

    def is_entry_allowed(self, current_time_str: str = None) -> bool:
        """Checks if new trades can be initiated (e.g. 09:30 to 11:30)."""
        t = current_time_str or self.get_current_time_str()
        return self.config.entry_start <= t <= self.config.entry_cutoff

    def is_square_off_time(self, current_time_str: str = None) -> bool:
        """Checks if mandatory square-off time has been reached (e.g. >= 15:15)."""
        t = current_time_str or self.get_current_time_str()
        return t >= self.config.square_off_time
