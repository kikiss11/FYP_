"""Job scheduling for automated weekly extraction."""

from datetime import datetime
from typing import Optional

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from ..config import settings
from .extractor import TrendsExtractor


class TrendsScheduler:
    """Scheduler for automated Google Trends extraction."""

    def __init__(self):
        """Initialize the scheduler."""
        self._scheduler: Optional[BackgroundScheduler] = None
        self._extractor = TrendsExtractor()
        self._is_running = False

    def _create_scheduler(self) -> BackgroundScheduler:
        """Create and configure the APScheduler instance."""
        jobstores = {
            "default": MemoryJobStore(),
        }
        executors = {
            "default": ThreadPoolExecutor(max_workers=2),
        }
        job_defaults = {
            "coalesce": True,  # Combine missed runs into one
            "max_instances": 1,  # Only one instance at a time
            "misfire_grace_time": 3600,  # 1 hour grace period
        }

        return BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

    def _job_extraction(self):
        """Job function for scheduled extraction."""
        logger.info("=" * 60)
        logger.info(f"⏰ Scheduled extraction triggered at {datetime.utcnow()}")
        logger.info("=" * 60)

        try:
            result = self._extractor.run_extraction(
                save_to_db=True,
                save_to_csv=True,
            )
            logger.success(f"Scheduled extraction completed: {result}")
        except Exception as e:
            logger.error(f"Scheduled extraction failed: {e}")

    def start(
        self,
        day_of_week: Optional[str] = None,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        run_immediately: bool = False,
    ):
        """
        Start the scheduler with weekly extraction job.

        Args:
            day_of_week: Day to run (mon, tue, wed, thu, fri, sat, sun)
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            run_immediately: Whether to run extraction immediately on start
        """
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        # Use settings or defaults
        day_of_week = day_of_week or settings.schedule_day_of_week
        hour = hour if hour is not None else settings.schedule_hour
        minute = minute if minute is not None else settings.schedule_minute

        # Create scheduler
        self._scheduler = self._create_scheduler()

        # Add weekly job
        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
        )

        self._scheduler.add_job(
            self._job_extraction,
            trigger=trigger,
            id="weekly_extraction",
            name="Weekly Google Trends Extraction",
            replace_existing=True,
        )

        # Start scheduler
        self._scheduler.start()
        self._is_running = True

        logger.success("=" * 60)
        logger.success("✅ Scheduler started!")
        logger.success(f"   Schedule: {day_of_week} at {hour:02d}:{minute:02d} UTC")
        logger.success(f"   Next run: {self.get_next_run_time()}")
        logger.success("=" * 60)

        # Optional immediate run
        if run_immediately:
            logger.info("Running immediate extraction...")
            self._job_extraction()

    def stop(self):
        """Stop the scheduler."""
        if self._scheduler and self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler stopped")

    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time."""
        if self._scheduler:
            job = self._scheduler.get_job("weekly_extraction")
            if job:
                return job.next_run_time
        return None

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self._is_running,
            "next_run": str(self.get_next_run_time()) if self.get_next_run_time() else None,
            "schedule": {
                "day_of_week": settings.schedule_day_of_week,
                "hour": settings.schedule_hour,
                "minute": settings.schedule_minute,
            },
        }

    def trigger_now(self):
        """Manually trigger extraction immediately."""
        logger.info("Manual extraction triggered")
        self._job_extraction()


# Global scheduler instance
_scheduler: Optional[TrendsScheduler] = None


def get_scheduler() -> TrendsScheduler:
    """Get or create the scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TrendsScheduler()
    return _scheduler


def start_scheduled_extraction():
    """Start scheduled extraction (convenience function)."""
    scheduler = get_scheduler()
    scheduler.start(run_immediately=False)

    # Keep the script running
    import time
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()
        print("\n👋 Scheduler stopped")


if __name__ == "__main__":
    start_scheduled_extraction()

