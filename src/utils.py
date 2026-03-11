import logging
import os
import sys
from datetime import datetime, timezone


def setup_logging():
    """Configure logging to both file and console."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler("uploader.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def get_scheduled_publish_time(schedule_time_str: str) -> str:
    """
    Returns ISO 8601 datetime string for tomorrow at the given time.
    Example schedule_time_str: "14:00" (UTC)
    """
    now = datetime.now(timezone.utc)
    target_time = datetime.strptime(schedule_time_str, "%H:%M").time()
    scheduled = datetime.combine(now.date(), target_time, tzinfo=timezone.utc)
    if scheduled <= now:
        # If today's time has passed, schedule for tomorrow
        scheduled = scheduled.replace(day=scheduled.day + 1)
    else:
        # If it's still in the future today, use tomorrow? Usually we want next day always.
        # But requirement says "next day at a specific time", so we always add one day.
        scheduled = scheduled.replace(day=scheduled.day + 1)
    return scheduled.isoformat()
