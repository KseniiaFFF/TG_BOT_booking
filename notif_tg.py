from assign_bot import bot
from log import logger
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from utils import format_route


kyiv_tz = ZoneInfo("Europe/Kyiv")

ADMIN_CHAT_ID = 5948335788


def notify_admin(text:str):
    try:
        bot.send_message(ADMIN_CHAT_ID, text)
    except Exception as e:
        logger.warning(f"Admin notify error:", e)


def schedule_notification(scheduler, booking_date, chat_id, route, seats):

    kyiv_tz = ZoneInfo("Europe/Kyiv")

    if booking_date.tzinfo is None:
        booking_date = booking_date.replace(tzinfo=kyiv_tz)

    notify_time = booking_date - timedelta(hours=20)

    now = datetime.now(kyiv_tz)

    if notify_time <= now:
        return

    scheduler.add_job(
        notify_client,
        trigger='date',
        run_date=notify_time,
        args=[booking_date, chat_id, route, seats],
        id=f"notify_{chat_id}_{booking_date}",
        replace_existing=True
    )


def notify_client(booking_date, chat_id, route, seats):

    logger.info(f"[NOTIFY] chat_id={chat_id}, type={type(chat_id)}")

    route_text = format_route(route)

    text = (
        f"⏰ Нагадування про поїздку\n\n"
        f"🚍 Маршрут: {route_text}\n"
        f"📅 Дата: {booking_date}\n"
        f"💺 Місця: {', '.join(map(str, seats))}"
    )

    bot.send_message(chat_id, text)
