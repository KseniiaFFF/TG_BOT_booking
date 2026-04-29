from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo
from notif_tg import schedule_notification
from notifications import sync
from db_file import cleanup_old_bookings,get_all_future_bookings

scheduler = BackgroundScheduler(timezone=ZoneInfo("Europe/Kyiv"))

def start_scheduler():

    scheduler.add_job(
        cleanup_old_bookings,
        trigger='cron',
        hour=3,
        minute=0,
        id="cleanup_job",
        replace_existing=True
    )

    scheduler.add_job(
        sync,
        trigger='cron',
        hour=3,
        minute=15,
        id="sync_job",
        replace_existing=True
    )

    scheduler.start()


def restore_jobs():

    bookings = get_all_future_bookings()

    for b in bookings:
        schedule_notification(
            scheduler,
            b["booking_date"],
            b["chat_id"],
            b["route"],
            b["seats"]
        )