from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from zoneinfo import ZoneInfo
from db_file import get_busy_seats


NAME_WEEKDAYS = {
    0:"Пн",
    1:"Вт",
    2:"Ср",
    3:"Чт",
    4:"Пт",
    5:"Сб",
    6:"Нд"
}

DEPARTURE_TIME = {
    "ua_md" : 7,
    "md_ua" : 6
}

WEEKDAYS = {
    "ua_md" : {2,4,6},
    "md_ua" : {0,3,5}
}


TOTAL_SEATS = 8


def is_date_full(route, date):
    busy = get_busy_seats(route, date)  
    return len(busy) >= TOTAL_SEATS


def get_available_dates(route, days_ahead=60):
    today = datetime.now(ZoneInfo("Europe/Kyiv"))
    result = []

    for i in range(days_ahead):
        day = today + timedelta(days=i)

        if day.weekday() not in WEEKDAYS[route]:
            continue

        departure_hour = DEPARTURE_TIME[route]
        departure_time = day.replace(hour=departure_hour, minute=40,second=0,microsecond=0)

        if departure_time <=today:
            continue

        result.append(day)

    return result


def paginate(items, page=0, per_page=9):
    start = page * per_page
    end = start + per_page
    return items[start:end]


def build_date_keyboard(route, page=0):
    dates = get_available_dates(route)
    page_items = paginate(dates, page)

    markup = InlineKeyboardMarkup(row_width=3)

    buttons = []

    for d in page_items:
        weekday_ua = NAME_WEEKDAYS[d.weekday()]
        date_str = d.strftime('%Y-%m-%d')

        is_full = is_date_full(route, date_str)

        
        if is_full:
            text = d.strftime(f"❌ %d.%m ({weekday_ua})")
            callback = f"{route}|full_{date_str}"
        else:
            text = d.strftime(f"%d.%m ({weekday_ua})")
            callback = f"{route}|date_{date_str}"

        buttons.append(InlineKeyboardButton(text, callback_data=callback))

    markup.add(*buttons)


    nav_buttons = []

    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{route}|page_{page-1}"))

    if len(paginate(dates, page + 1)) > 0:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"{route}|page_{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)

    markup.row(InlineKeyboardButton('🔙Назад', callback_data=f"{route}|back"))

    return markup


