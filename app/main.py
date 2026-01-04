"""
Main entry point for the Pizza Index Tracker Bot.

Run with: python -m app.main
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.monitoring import PizzaMonitor, SignalDetector


def setup_logging() -> logging.Logger:
    """Configure application logging."""
    log_format = "[%(asctime)s] %(name)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Ensure log directory exists
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(settings.LOG_DIR / "pizza_bot.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    return logging.getLogger(__name__)


logger = logging.getLogger(__name__)


class PizzaIndexBot:
    """
    Main bot application.

    Coordinates monitoring, analysis, decision-making, and execution.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.PizzaIndexBot")
        self.scheduler = AsyncIOScheduler()
        self.shutdown_event = asyncio.Event()
        self._pizza_monitor: PizzaMonitor | None = None
        self._signal_detector: SignalDetector | None = None

    async def monitor_and_trade(self) -> None:
        """
        Main trading loop - runs on schedule.

        1. Fetch pizza index data
        2. Detect signals
        3. Track trader activity
        4. Make trading decisions
        5. Execute trades (or simulation)
        """
        self.logger.info("=== Starting trading cycle ===")

        try:
            # TODO: Phase 2 - Fetch pizza data and detect signals
            await self._fetch_pizza_data()

            # TODO: Phase 3 - Track trader activity
            # await self._track_traders()

            # TODO: Phase 4 - Make decisions
            # decisions = await self._make_decisions()

            # TODO: Phase 5 - Execute trades
            # await self._execute_trades(decisions)

        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}", exc_info=True)

        finally:
            self.logger.info("=== Trading cycle complete ===\n")

    async def _fetch_pizza_data(self) -> None:
        """Fetch pizza index data from PizzINT API."""
        self.logger.info("Fetching pizza index data...")

        try:
            if self._pizza_monitor is None:
                self._pizza_monitor = PizzaMonitor(settings.PIZZA_API_URL)

            if self._signal_detector is None:
                self._signal_detector = SignalDetector(
                    defcon_threshold=settings.DEFCON_THRESHOLD,
                    spike_threshold=settings.SPIKE_THRESHOLD,
                    confidence_threshold=settings.CONFIDENCE_THRESHOLD,
                )

            pizza_data = await self._pizza_monitor.fetch()

            self.logger.info(
                f"Pizza Index: {pizza_data.overall_index}, "
                f"DEFCON: {pizza_data.defcon_level}, "
                f"Active Spikes: {pizza_data.active_spikes}"
            )

            if change := self._pizza_monitor.get_defcon_change():
                direction = "dropped" if change > 0 else "increased"
                prev_defcon = self._pizza_monitor._last_defcon
                curr_defcon = self._pizza_monitor._last_data.defcon_level if self._pizza_monitor._last_data else 0
                self.logger.info(f"DEFCON {direction} by {abs(change)} (from {prev_defcon} to {curr_defcon})")

            signals = self._signal_detector.analyze(pizza_data)

            if signals:
                self.logger.info(f"Detected {len(signals)} signal(s):")
                for signal in signals:
                    self.logger.info(
                        f"  - {signal.type.value}: "
                        f"confidence={signal.confidence:.2f}, "
                        f"data={signal.data}"
                    )
            else:
                self.logger.debug("No signals detected")

        except Exception as e:
            self.logger.error(f"Error fetching pizza data: {e}", exc_info=True)

    async def health_check(self) -> None:
        """Periodic health check - runs every minute."""
        self.logger.debug("Health check - bot is running")

    async def startup(self) -> None:
        """Initialize and start the bot."""
        self.logger.info("=" * 60)
        self.logger.info("Pizza Index Tracker Bot v0.1.0")
        self.logger.info("=" * 60)
        self.logger.info(f"Mode: {'SIMULATION' if settings.SIMULATION_MODE else 'LIVE TRADING'}")
        self.logger.info(f"Strategy: {settings.STRATEGY.upper()}")
        self.logger.info(f"Poll Interval: {settings.POLL_INTERVAL_MINUTES} minutes")
        self.logger.info(f"Database: {settings.DATABASE_URL}")
        self.logger.info("=" * 60)

        # Schedule main trading loop
        self.scheduler.add_job(
            self.monitor_and_trade,
            "interval",
            minutes=settings.POLL_INTERVAL_MINUTES,
            id="main_trading_loop",
            max_instances=1,
        )

        # Schedule health check
        self.scheduler.add_job(
            self.health_check,
            "interval",
            minutes=1,
            id="health_check",
        )

        self.scheduler.start()
        self.logger.info("Scheduler started")

    async def shutdown(self) -> None:
        """Gracefully shutdown the bot."""
        self.logger.info("Shutting down...")

        if self._pizza_monitor:
            await self._pizza_monitor.close()

        self.scheduler.shutdown(wait=False)
        self.logger.info("Shutdown complete")

    async def run(self) -> None:
        """Run the bot until shutdown signal."""
        await self.startup()

        # Run one cycle immediately on startup
        await self.monitor_and_trade()

        # Wait for shutdown signal
        await self.shutdown_event.wait()

        await self.shutdown()


def signal_handler(bot: PizzaIndexBot):
    """Handle shutdown signals gracefully."""
    def handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        bot.shutdown_event.set()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


async def main() -> int:
    """Main entry point."""
    setup_logging()

    bot = PizzaIndexBot()
    signal_handler(bot)

    try:
        await bot.run()
        return 0
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
