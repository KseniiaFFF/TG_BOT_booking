import threading

from assign_bot import bot
from log import logger
from user_menu import show_booking_admin, adm_keyboard, book_a_place, contact_us, main_menu, user_state, send_dates, ask_phone, waiting_answer, cancel_keyboard, get_state, admin_menu, admin_menu_2, show_blocked_users
from db_file import update_booking, get_connection, init_db, add_or_update_user, delete_booking, search_users, init_db_block, block_user
from phone_module import is_valid_ua_phone, normalize_phone
from notifications import sync
from scheduler import start_scheduler, restore_jobs
from notif_tg import ADMIN_CHAT_ID
from utils import apply_departure_time

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("✅ Подключение успешно")
        start_scheduler()
        restore_jobs()
        conn.close()
    except Exception as e:
        print("❌ Ошибка:", e)

init_db()
init_db_block()


def get_user_data(message):
    return message.chat.id, message.chat.username


@bot.message_handler(commands=["start"])
def start(message):

    chat_id, user_name = get_user_data(message)
    state = get_state(chat_id)
    state["step"] = "main_menu"

    logger.info(f'commands "start"| user_name = {user_name}, chat_id = {chat_id}')  

    if chat_id == ADMIN_CHAT_ID:
        admin_menu(message)
    else:

        bot.send_message(
            chat_id,
            "Здесь приветственное сообщение"
        )
    
        threading.Timer(1, main_menu, args=(message,)).start()


BUTTON_HANDLERS = {
    '🚌Обрати маршрут': book_a_place,
    '✍️Змінити дані бронювання' : book_a_place,
    'ℹ️Контакти та допомога': contact_us,
    'Головне меню' : main_menu,
    '❌Скасування' : main_menu,
    'Адмін меню' : admin_menu
}    


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    state = get_state(chat_id)
    step = state.get("step")

    if step != "waiting_phone":
        return

    phone = message.contact.phone_number

    user_state[chat_id]["phone"] = phone
    user_state[chat_id]["step"] = "waiting_pib"

    bot.send_message(chat_id, "✍️ Введіть ПІБ", reply_markup=cancel_keyboard())


@bot.message_handler(func=lambda m: m.text == "🙌Створити бронювання")
def admin_create_booking(message):

    chat_id = message.chat.id

    import time
    fake_id = int(time.time())

    user_state[chat_id] = {
        "step":"admin_enter_name",
        "target":fake_id
    }

    book_a_place(message)


@bot.message_handler(content_types=['text'])
def router(message):
    chat_id, user_name = get_user_data(message)
    text = message.text.strip()

    state = get_state(chat_id)
    step = state.get("step")


    if text == "🔙Назад":
        
        if step == 'book_a_place':
            main_menu(message)
        elif step == 'booking_details':
            book_a_place(message)  
        elif step == 'choosing_date':
            book_a_place(message)
        else:
            main_menu(message)                    
        
        return

    handler = BUTTON_HANDLERS.get(text)

    if handler:
        handler(message)
        return
    
    if step == 'book_a_place':
        if text == '🇺🇦 Черкаси - Кишинів 🇲🇩':
            bot.send_message(chat_id, "Відправлення по середам, п'ятницях та неділях о 7-й ранку")
            send_dates(message, "ua_md")
            return
        if text == '🇲🇩 Кишинів - Черкаси 🇺🇦':
            bot.send_message(chat_id, "Відправлення у понеділок, четвер, суботу о 6-й ранку")
            send_dates(message, "md_ua")
            return
        
    if step == "check_booking":

        if text == "❌ Ні":
            book_a_place(message)
            return

        if text == "✅ Так":
            user_state[chat_id]["step"] = "waiting_phone"
            ask_phone(message)
            return
        

    if step == 'waiting_phone':
        phone = normalize_phone(message.text)

        if not is_valid_ua_phone(phone):
            bot.send_message(chat_id, "❌ Невірний формат")
            return

        user_state[chat_id]["phone"] = phone
        user_state[chat_id]["step"] = "waiting_pib"

        bot.send_message(chat_id, "✍️ Введіть ПІБ", reply_markup=cancel_keyboard())
        return
    

    if step == "waiting_pib":

        pib = text.strip()

        if len(pib) < 3:
            bot.send_message(chat_id, "❌ Введіть коректне ПІБ")
            return

        user_state[chat_id]["pib"] = pib
        user_state[chat_id]["step"] = "confirm_booking"

        state = user_state[chat_id]
        route_map = {
                "ua_md": "🇺🇦 Черкаси - Кишинів 🇲🇩",
                "md_ua": "🇲🇩 Кишинів - Черкаси 🇺🇦"
            }

        route = route_map.get(state.get("route"), "Невідомий маршрут")
            
        seats = ", ".join(map(str, state["seats"]))
        bot.send_message(
            chat_id,
            f"""🚍 Бронювання:

        Маршрут: {route}
        Дата: {state['date']}
        Місця: {seats}
        Телефон: {state['phone']}
        ПІБ: {state['pib']}

        Вірно?""",
                    reply_markup=waiting_answer()
                )
        return
    
    if step == "confirm_booking":
        seat_number = [int(s) for s in state['seats']]

        if text == "❌ Ні":
            main_menu(message)
            return

        if text == "✅ Так":
            state = user_state[chat_id]

            add_or_update_user(
                # chat_id,
                state["target"],
                username=user_name,
                name=state['pib'],
                phone=state['phone'],
                route=state['route'],
                booking_date=state['date'],
                seat_number=seat_number
            )

        bot.send_message(chat_id, "✅ Бронювання збережено!")

        if chat_id == ADMIN_CHAT_ID:
            admin_menu(message)
        else:
            main_menu(message)
        sync()
        return
    
    if text == '❌Скасувати поїздку':
        success, status = delete_booking(chat_id, force=False)

        if status == "too_late":
            bot.send_message(chat_id, "❌ Скасування неможливе менш ніж за 2 дні до відправлення")
            return
        elif status == "deleted":
            bot.send_message(chat_id, "✅ Бронювання скасовано")
            main_menu(message)
            sync()
            return
        
    if step == "admin_menu":
        if text == "🔍 Знайти клієнта":
            user_state[chat_id]["step"]="admin_search"
            bot.send_message(chat_id, "Введіть дані клієнта", reply_markup=adm_keyboard())
            return
        
        if text == "🚫 Чорний список":
            show_blocked_users(message)
            return
        
        if text == "➕ Додати в ЧС":
            user_state[chat_id]["step"] = "block_user_manual"
            bot.send_message(chat_id, "Введіть chat_id користувача:", reply_markup=adm_keyboard())
            return
        
    if step == "block_user_manual":
        try:
            target_id = int(text)
        except:
            bot.send_message(chat_id, "❌ Невірний ID")
            return
        block_user(target_id)
        bot.send_message(chat_id, "✅ Користувача заблоковано")
        user_state[chat_id]["step"] = "admin_menu"
        return

    if step == "admin_search":
            
            query = text
    
            results = search_users(query)

            if not results:
                bot.send_message(chat_id, "Not find")
                return
            
            bot_text = ""

            selected_user_id = results[0][0]
            
            for r in results:
                bot_text += (
                    f"👤 {r[2]} (@{r[1]})\n"
                    f"📱 {r[3]}\n"
                    f"🚍 {r[4]}\n"
                    f"📅 {r[5]}\n"
                    f"💺 {r[6]}\n\n"
                )

            bot.send_message(chat_id, bot_text)

            user_state.setdefault(chat_id,{})["selected_user_id"] = selected_user_id
            user_state[chat_id]["step"]="choose_action"
            admin_menu_2(message)
            return 
    
    if step == "choose_action":
        if text == "🚫 У чорний список":
            selected_user_id = user_state.get(chat_id, {}).get("selected_user_id")

            if not selected_user_id:
                bot.send_message(chat_id, "❌ Користувача не знайдено")
                return
            block_user(selected_user_id)
            bot.send_message(chat_id, "Додано успішно👌", reply_markup=admin_menu(message))
            user_state[chat_id]["step"]="admin_menu"
            return
        elif text == "✏️Змінити дані бронювання":
            selected_user_id = user_state.get(chat_id, {}).get("selected_user_id")
            bot.send_message(chat_id, "Що треба змінити?", reply_markup=adm_keyboard())
            show_booking_admin(message, selected_user_id)
            return

    if step == "edit_date_inline":
        target = user_state[chat_id]["target"]

        try:
            new_date = apply_departure_time(text)
            update_booking(target, booking_date = new_date)

            bot.send_message(chat_id, "✅ Дату оновлено")

            show_booking_admin(message, target)
            sync()
            user_state[chat_id]["step"] = "admin_menu"
            return
        except:
            bot.send_message(chat_id, "❌ Невірний формат")

    if step == "edit_name":
        target = state.get("target")

        if not target:
            bot.send_message(chat_id, "❌ Помилка")
            return
        
        update_booking(target, name = text)
        bot.send_message(chat_id, "✅ Ім'я оновлено")
        sync()
        show_booking_admin(message,target)
        user_state[chat_id]["step"] = "admin_menu"
        return
    
    if step == "edit_phone":
        target = state.get("target")

        if not target:
            bot.send_message(chat_id, "❌ Помилка")
            return
        
        update_booking(target, phone = text)
        bot.send_message(chat_id, "✅ Номер оновлено")
        sync()
        show_booking_admin(message,target)
        user_state[chat_id]["step"] = "admin_menu"
        return
    
    bot.send_message(
        chat_id,
        "Використовуйте кнопки меню 👇"
    ) 
    

bot.polling()