from db_file import get_busy_seats
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def build_seats_keyboard(route_id, date, selected=None):
    markup = InlineKeyboardMarkup(row_width=3)

    busy = get_busy_seats(route_id, date)
    selected = set(selected or [])

    buttons = []

    for i in range(1, 9):

        if i in busy:
            text = f"⛔ {i}"
            callback = "noop"

        elif i in selected:
            text = f"✅ {i}"
            callback = f"{route_id}|toggle_{i}"

        else:
            text = str(i)
            callback = f"{route_id}|toggle_{i}"

        buttons.append(
            InlineKeyboardButton(text=text, callback_data=callback)
        )

    markup.add(*buttons)

    markup.row(
        InlineKeyboardButton("➡️ Далі", callback_data=f"{route_id}|next")
    )

    markup.row(
        InlineKeyboardButton("🔙Назад", callback_data=f"{route_id}|back")
    )

    return markup


def build_admin_seats_keyboard(route, date, selected_seats=None):
    if selected_seats is None:
        selected_seats = []

    busy = get_busy_seats(route, date)

    markup = InlineKeyboardMarkup(row_width=4)

    for seat in range(1, 9):  
        text = str(seat)

        if seat in busy and seat not in selected_seats:
            text = f"❌{seat}"

        elif seat in selected_seats:
            text = f"✅{seat}"

        markup.add(
            InlineKeyboardButton(
                text=text,
                callback_data=f"adm_seat_{seat}"
            )
        )

    markup.add(
        InlineKeyboardButton("💾 Зберегти зміни", callback_data="adm_save"),
        InlineKeyboardButton("🔙 Назад", callback_data="adm_back")
    )

    return markup


