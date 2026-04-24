from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo
from notif_tg import schedule_notification

scheduler = BackgroundScheduler(timezone=ZoneInfo("Europe/Kyiv"))

def start_scheduler():

    from db_file import cleanup_old_bookings

    scheduler.add_job(
        cleanup_old_bookings,
        trigger='cron',
        hour=3,
        minute=0,
        id="cleanup_job",
        replace_existing=True
    )
    scheduler.start()


def restore_jobs():

    from db_file import get_all_future_bookings

    bookings = get_all_future_bookings()

    for b in bookings:
        schedule_notification(
            scheduler,
            b["booking_date"],
            b["chat_id"],
            b["route"],
            b["seats"]
        )