import logging
import time
from datetime import datetime, timedelta

from invoicing.models import CachedData, GlobalConfiguration
from invoicing.utils.settings import SettingsInfo
from invoicing.utils.purchase_invoice_generation import fetch_purchase_invoices_for_session

from cz_utils.utils import in_ist

logger = logging.getLogger(__name__)


def india_time(time):
    """
    The current time in India
    """
    return in_ist(time)


def create_scheduled_task():
    logger.info("Creating autosync scheduled task")
    cd = CachedData(datatype=CachedData.DT_PURCHASE_SESSION_MARKER)
    cd.full_clean()
    cd.save()
    fetch_purchase_invoices_for_session.delay(0)(session_uuid=str(cd.uuid), is_autorun=True)


def does_time_match_schedule_to_the_minute(schedule, now):
    """
    Checks if the scheduled time matches with the current time upto minutes granularity
    """
    scheduled_interval = schedule["minutes"]
    scheduled_start_hour = int(schedule["start_hour"])
    scheduled_end_hour = int(schedule["end_hour"])
    scheduled_days_for_sync = schedule["weekdays"]
    DOW = now.strftime("%A")
    current_hour = now.hour
    minutes = now.minute + (now.hour * 60)
    logger.info(
        "Checking for schedule now=%s DOW=%s scheduled_start_hour=%s current_hour=%s "
        "scheduled_end_hour=%s minutes=%s scheduled_interval=%s",
        now,
        DOW,
        scheduled_start_hour,
        current_hour,
        scheduled_end_hour,
        minutes,
        scheduled_interval,
    )
    if DOW not in scheduled_days_for_sync:
        return False
    if not (scheduled_start_hour <= current_hour <= scheduled_end_hour):
        return False
    if current_hour == scheduled_end_hour and now.minute > 0:
        return False
    if minutes % scheduled_interval == 0:
        return True
    return False


def does_time_match_schedule(schedule, now):
    """
    Checks if the scheduled time matches with the current time upto seconds granularity
    """
    offset = timedelta(seconds=45)
    return does_time_match_schedule_to_the_minute(
        schedule=schedule, now=(now - offset)
    ) or does_time_match_schedule_to_the_minute(schedule=schedule, now=(now + offset))


def schedule_autosync_iteration():
    try:
        si = SettingsInfo(GlobalConfiguration.get_solo())
        schedule = si.autosync_settings
        if not schedule:
            return
        now = india_time(datetime.now())
        if does_time_match_schedule(schedule=schedule, now=now):
            create_scheduled_task()
    except Exception:
        logger.exception("While creating auto-sync scheduled task")


def schedule_autosync():
    """
    Schedules the Auto-sync when required
    """
    while True:
        schedule_autosync_iteration()
        logger.info("Back to sleep")
        time.sleep(60)


