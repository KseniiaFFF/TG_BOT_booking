from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from assign_bot import bot
from dates_file import build_date_keyboard
from db_file import is_book_active, is_user_blocked, get_blocked_users, unblock_user, get_full_booking, update_booking, delete_booking
from seats_create import build_seats_keyboard, build_admin_seats_keyboard
from log import logger
from utils import format_route, parce_seats
from notifications import sync


user_state = {}

def get_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {}
    return user_state[chat_id]


def main_menu(message):

    chat_id = message.chat.id

    if is_user_blocked(chat_id):
        bot.send_message(chat_id, "🚫 Ви заблоковані")
        return

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if is_book_active(chat_id):
        keyboard.add(types.KeyboardButton("❌Скасувати поїздку"))
        keyboard.add(types.KeyboardButton("✍️Змінити дані бронювання"))
    else:
        keyboard.add(types.KeyboardButton("🚌Обрати маршрут"))

    keyboard.add(types.KeyboardButton("ℹ️Контакти та допомога"))


    bot.send_message(
        chat_id,
        "Виберіть дію:",
        reply_markup=keyboard
    )
    user_state[chat_id]["step"]="main_menu"


def admin_menu(message):

    chat_id = message.chat.id

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔍 Знайти клієнта", "🚫 Чорний список", "➕ Додати в ЧС")
    keyboard.add("🙌Створити бронювання")
    
    bot.send_message(chat_id,"Admin menu", reply_markup=keyboard)

    user_state[chat_id]["step"]="admin_menu"


def admin_menu_2(message):

    chat_id = message.chat.id
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    keyboard.add("🚫 У чорний список", "✏️Змінити дані бронювання")
    keyboard.add(types.KeyboardButton("Адмін меню"))
    
    bot.send_message(chat_id, "Оберіть дію", reply_markup=keyboard)


def show_blocked_users(message):

    chat_id = message.chat.id

    users = get_blocked_users()

    if not users:
        bot.send_message(chat_id, "black list is empty")
        return
    
    text = "🚫 Заблоковані користувачі:\n\n"

    for u in users:
        text +=f"{u[0]}\n {u[1]}\n\n"

    murkup = build_blocked_users_keyboard(users)

    bot.send_message(chat_id, text, reply_markup=murkup)


def build_blocked_users_keyboard(users):
    murkup = InlineKeyboardMarkup()

    for chat_id, created_at in users:
        murkup.add(
            InlineKeyboardButton(
                text=f"❌ Розблокувати {chat_id}",
                callback_data=f"unblock_{chat_id}"
            )
        )
    return murkup

def build_booking_text(booking):
    route_text = format_route(booking["route"])
    seats = parce_seats(booking.get("seat_number"))

    return (
        f"👤 ID: {booking['chat_id']}\n"
        f"👤 {booking['name']} (@{booking['username']})\n"
        f"📱 {booking['phone']}\n\n"
        f"🚍 {route_text}\n"
        f"📅 {booking['booking_date']}\n"
        f"💺 {', '.join(map(str, seats)) if seats else 'нема'}"
    )

def show_booking_admin(message, target_user_id):
    booking = get_full_booking(target_user_id)

    if not booking:
        bot.send_message(message.chat.id, "❌ Бронь не знайдена")
        return

    text = build_booking_text(booking)

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=booking_inline_keyboard(target_user_id)
    )


def booking_inline_keyboard(target_user_id):
    murkup = InlineKeyboardMarkup(row_width=2)

    murkup.add(
        InlineKeyboardButton("✏️ Дата",callback_data=f"edit|date_admin|{target_user_id}"),
        InlineKeyboardButton("💺 Места",callback_data=f"edit|seats_admin|{target_user_id}"),
        InlineKeyboardButton("🚌 Маршрут",callback_data=f"edit|route_admin|{target_user_id}")
    )

    murkup.add(
        InlineKeyboardButton("👤Ім'я",callback_data=f"edit|name_admin|{target_user_id}"),
        InlineKeyboardButton("📞Номер",callback_data=f"edit|phone_admin|{target_user_id}"),
        InlineKeyboardButton("❌Скасувати бронювання",callback_data=f"edit|delete|{target_user_id}")
    )

    murkup.add(
        InlineKeyboardButton("👈Назад",callback_data="edit|admin_back")
    )

    return murkup


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit|"))
def edit_booking_handler(call):

    data = call.data.split("|")
    action = data[1]

    if action == "admin_back":
        admin_menu(call.message)
        return
    
    target_user_id = int(data[2])

    if action == "delete":
        success, status = delete_booking(target_user_id, force=True)

        if status == "deleted":
                bot.edit_message_text(
                    "✅ Бронювання видалено",
                    call.message.chat.id,
                    call.message.message_id
                )
                user_state[call.message.chat.id]["step"]="admin_menu"
                admin_menu(call.message)
                sync()
                return
        elif status == "not_found":
            bot.edit_message_text(call.message.chat.id, "❌ Бронювання не знайдено")
            return
        else:
            bot.edit_message_text(call.message.chat.id, "Щось пішло не так")
            return

    if action == "date_admin":
        user_state[call.message.chat.id] = {
            "step": "edit_date_inline",
            "target": target_user_id
        }
        bot.send_message(call.message.chat.id, "Введіть нову дату (YYYY-MM-DD)")
        return
    
    if action == "route_admin":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🇺🇦 UA → MD", callback_data=f"setroute|ua_md|{target_user_id}"),
            InlineKeyboardButton("🇲🇩 MD → UA", callback_data=f"setroute|md_ua|{target_user_id}")
        )
        bot.send_message(call.message.chat.id,"Оберіть маршрут:", reply_markup=markup)
        return
    
    if action == "seats_admin":
        booking = get_full_booking(target_user_id)
        selected = parce_seats(booking.get("seat_number"))

        if not booking:
            bot.answer_callback_query(call.id, "❌ Бронь не знайдена")
            return
        
        booking_date = booking["booking_date"]

        if hasattr(booking_date,"date"):
            booking_date = booking_date.date().isoformat()
        else:
            booking_date = str(booking_date)[:10]

        user_state[call.message.chat.id] = {
            "step": "edit_seats",
            "target": target_user_id,
            "route": booking["route"],
            "date": booking_date,
            "seats":[]
        }

        bot.send_message(
            call.message.chat.id,
            "Оберіть місця:",
            reply_markup=build_admin_seats_keyboard(
                booking["route"],
                booking_date,
                selected
            )
        )
        return
    
    if action == "name_admin":
        user_state[call.message.chat.id] = {
            "step":"edit_name",
            "target":target_user_id
        }
        bot.send_message(call.message.chat.id, "Введіть нове ім'я:")
        return
    
    if action == "phone_admin":
        user_state[call.message.chat.id] = {
            "step":"edit_phone",
            "target":target_user_id
        }
        bot.send_message(call.message.chat.id, "Введіть новий номер:")
        return

    

@bot.callback_query_handler(func=lambda call: call.data == "adm_back")
def admin_back(call):
    show_booking_admin(call.message, user_state[call.message.chat.id]["target"])


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_seat_"))
def admin_seat_handler(call):
    chat_id = call.message.chat.id
    seat = int(call.data.split("_")[2])

    state = user_state.setdefault(chat_id, {})

    if state.get("step") != "edit_seats":
        return

    selected = state.setdefault("seats", [])

    if seat in selected:
        selected.remove(seat)
    else:
        selected.append(seat)

    bot.edit_message_reply_markup(
        chat_id,
        call.message.message_id,
        reply_markup=build_admin_seats_keyboard(
            state["route"],
            state["date"],
            selected
        )
    )


@bot.callback_query_handler(func=lambda call: call.data == "adm_save")
def admin_save_seats(call):
    chat_id = call.message.chat.id
    state = user_state.get(chat_id, {})

    target = state.get("target")
    seats = state.get("seats", [])

    if not target:
        bot.answer_callback_query(call.id, "❌ Помилка")
        return

    update_booking(target, seat_number=seats)

    bot.answer_callback_query(call.id, "✅ Оновлено")
    bot.send_message(chat_id, "Бронювання оновлено")

    show_booking_admin(call.message, target)
    sync()
    

@bot.callback_query_handler(func=lambda call: call.data.startswith("setroute|"))
def set_route_handler(call):

    _,route,user_id = call.data.split("|")

    update_booking(int(user_id), route = route)

    bot.send_message(call.message.chat.id, "✅ Маршрут оновлено")
    sync()

    show_booking_admin(call.message, int(user_id))


@bot.callback_query_handler(func=lambda call: call.data.startswith("unblock_"))
def handle_unblock(call):

    admin_chat_id = call.message.chat.id

    user_id = int(call.data.split("_")[1])

    unblock_user(user_id)

    bot.answer_callback_query(call.id, "✅ Користувача розблоковано")

    users = get_blocked_users()
    murkup = build_blocked_users_keyboard(users)

    bot.edit_message_reply_markup(
        chat_id=admin_chat_id,
        message_id=call.message.message_id,
        reply_markup=murkup
    )



def cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("❌Скасування"))
    return keyboard


def adm_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Адмін меню"))
    return keyboard


def book_a_place(message):

    chat_id = message.chat.id

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.add(
        types.KeyboardButton('🇺🇦 Черкаси - Кишинів 🇲🇩'),
        types.KeyboardButton('🇲🇩 Кишинів - Черкаси 🇺🇦'),
    )
    keyboard.add(types.KeyboardButton('🔙Назад'))

    bot.send_message(
        message.chat.id,
        'Оберіть маршрут: ',
        reply_markup=keyboard
    )   

    user_state[chat_id]["step"] = "book_a_place"


def contact_us(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            text="Зв’язатися з нами:",
            url="https://t.me/Kseniia999"
        )
    )

    bot.send_message(
        message.chat.id,
        "Натисніть кнопку нижче👇:",
        reply_markup=markup
    )


def send_dates(message, route):

    chat_id = message.chat.id
    user_state[chat_id]["step"] = "choosing_date"
    user_state[chat_id]["route"] = route
    

    bot.send_message(
        chat_id,
        "Оберіть дату відправлення:",
        reply_markup=types.ReplyKeyboardRemove()
    )

    bot.send_message(
        chat_id,
        "👇 доступні дати:",
        reply_markup=build_date_keyboard(route, 0)
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    chat_id = call.message.chat.id

    if "|" not in data:
        return
    
    route, action = data.split("|", 1)


    if action.startswith("page_"):
        handle_page(call, route, action)
        return

    if action.startswith("date_"):
        handle_date(call, route, action)
        return

    if action.startswith("seat_"):
        handle_seat(call, route, action)
        return
    
    if action == "next":
        handle_seat_next(call, route, action)
        return

    if action == "back":
        handle_back(call, route)
        return
    
    if action == "noop":
        bot.answer_callback_query(call.id, "❌ Місце зайняте")
        return
    
    if action.startswith("full_"):
        bot.answer_callback_query(call.id, "❌ На цю дату місць немає")
        return
    
    if action.startswith("toggle_"):
        seat = int(action.split("_")[1])

        state = user_state.setdefault(chat_id, {})
        selected = user_state.setdefault(chat_id, {}).setdefault("seats", [])

        if seat in selected:
            selected.remove(seat)
        else:
            selected.append(seat)

        state["seats"] = selected

        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=build_seats_keyboard(route, state.get("date"), selected)
        )
        return
        
    

def handle_back(call, route):
    book_a_place(call.message)


def handle_date(call, route, action):

    chat_id = call.message.chat.id

    selected_date = action.split("_")[1]

    user_state[chat_id]["step"] = "choosing_seat"
    user_state[chat_id]["route"] = route
    user_state[chat_id]["date"] = selected_date
    user_state[chat_id]["seats"] = []
    

    bot.send_photo(
        chat_id,
        open("bus_bot/bus_image.jpg", "rb"),
        caption=f"🚍Маршрут: {route}\n📅Дата: {selected_date}\n\nОберіть місця в автобусі:",
        reply_markup=build_seats_keyboard(route, selected_date)
    )

    return
    

def handle_page(call, route, action):
    chat_id = call.message.chat.id

    page = int(action.split("_")[1])

    bot.edit_message_reply_markup(
            chat_id,
            call.message.message_id,
            reply_markup=build_date_keyboard(route, page)
        )


def handle_seat(call, route, action):
    chat_id = call.message.chat.id

    seat = int(action.split("_")[1])

    state = user_state.setdefault(chat_id, {})
    selected = state.setdefault("seats", [])

    if seat in selected:
        selected.remove(seat)
    else:
        selected.append(seat)

    state["seats"] = selected

    date = state.get("date")

    bot.edit_message_reply_markup(
        chat_id,
        call.message.message_id,
        reply_markup=build_seats_keyboard(route, date, selected)
    )


def handle_seat_next(call, route, action):

    chat_id = call.message.chat.id
    state = get_state(chat_id)
    seats = state.get("seats", [])
    date = state.get("date")

    if not seats:
        bot.answer_callback_query(call.id, "Оберіть хоча б одне місце")
        return

    bot.send_message(
        chat_id,
        f"🚍Маршрут: {route}\n📅Дата: {date}\n💺Місця: {", ".join(map(str, seats))}\n\nВірно?",
        reply_markup=waiting_answer()
    )

    user_state[chat_id]["step"] = "check_booking"


def waiting_answer():

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton("✅ Так"),
        types.KeyboardButton("❌ Ні")
    )

    return keyboard


def ask_phone(message):

    chat_id = message.chat.id
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    button = types.KeyboardButton(
        text="📱 Поділитися номером",
        request_contact=True
    )

    keyboard.add(button)

    user_state[chat_id]["step"]="waiting_phone"
    

    bot.send_message(
        message.chat.id,
        "📞Натисніть кнопку, щоб поділитися номером або введіть номер:",
        reply_markup=keyboard
    )
    


