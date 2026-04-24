from telebot import types
from assign_bot import bot
from dates_file import build_date_keyboard
from db_file import is_book_active
from seats_create import build_seats_keyboard
from log import logger


user_state = {}

def get_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {}
    return user_state[chat_id]


def main_menu(message):

    chat_id = message.chat.id

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


def cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("❌Скасування"))
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
    


