import os
import psycopg

from dotenv import load_dotenv
from log import logger
from utils import apply_departure_time, format_route
from notif_tg import notify_admin
from datetime import datetime, timedelta, timezone


load_dotenv()

def get_connection():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bus_bot (
            chat_id BIGINT PRIMARY KEY,
            username TEXT,
            name TEXT,
            phone TEXT,
            route TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            booking_date TIMESTAMP WITH TIME ZONE,
            seat_number INTEGER[]
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def init_archive_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_clients (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            username TEXT,
            name TEXT,
            phone TEXT,
            route TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            booking_date TIMESTAMP WITH TIME ZONE,
            seat_number INTEGER[]
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def init_db_block():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked_users (
            chat_id BIGINT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW()
        )     
    """)
    conn.commit()
    cur.close()
    conn.close()


def block_user(chat_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO blocked_users (chat_id)
        VALUES (%s)
        ON CONFLICT (chat_id) DO NOTHING
    """, (chat_id,))

    conn.commit()
    cur.close()
    conn.close()


def unblock_user(chat_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM blocked_users
        WHERE chat_id = %s
    """, (chat_id,))

    conn.commit()
    cur.close()
    conn.close()


def is_user_blocked(chat_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM blocked_users
        WHERE chat_id = %s
    """, (chat_id,))

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result is not None


def get_blocked_users(limit=20):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT chat_id, created_at
        FROM blocked_users
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows
    

def get_busy_seats(route: str, date: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT seat_number, chat_id
        FROM bus_bot
        WHERE route = %s
        AND booking_date::date = %s::date
    """, (route, date))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    busy = set()

    for seats, _ in rows:

        if not seats:
            continue

        if isinstance(seats, str):
            seats = seats.replace(" ", " ").split(",")

        for s in seats:
            try:
                busy.add(int(s))
            except Exception:
                logger.warning(f"[PARSE ERROR] seat={s}")


    return busy


def add_or_update_user(chat_id: int, username: str = None, name: str = None, phone: str = None, route: str = None, booking_date: str = None, seat_number=None):
    conn = get_connection()
    cur = conn.cursor()

    if seat_number is not None:
        if isinstance(seat_number, str):
            seat_number = [int(s) for s in seat_number.split(",")]
        else:
            seat_number = [int(s) for s in seat_number]

    if booking_date is not None:
        booking_date = apply_departure_time(booking_date)
    
    cur.execute("""
        INSERT INTO bus_bot (chat_id, username, name, phone, route, created_at, booking_date, seat_number)
        VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)
        ON CONFLICT (chat_id) 
        DO UPDATE 
        SET username = EXCLUDED.username,
            name = EXCLUDED.name,
            phone = EXCLUDED.phone,
            route = COALESCE(EXCLUDED.route, bus_bot.route),
            booking_date = COALESCE(EXCLUDED.booking_date, bus_bot.booking_date),
            seat_number = COALESCE(EXCLUDED.seat_number, bus_bot.seat_number)
    """, (chat_id, username, name, phone, route, booking_date, seat_number))
    
    conn.commit()
    cur.close()
    conn.close()

    route_text = format_route(route)

    notify_admin(
        f"🆕 БРОНЬ ОНОВЛЕНО\n"
        f"👤 chat_id: {chat_id}\n"
        f"📱 phone: {phone}\n"
        f"🚍 route: {route_text}\n"
        f"📅 date: {booking_date}\n"
        f"💺 seats: {seat_number}"
    )

    logger.info(f"✅ Пользователь {chat_id}, {username} сохранён/обновлён")


def is_book_active(chat_id):
    with get_connection() as conn:
        cursor = conn.execute("""
        SELECT chat_id FROM bus_bot
        WHERE chat_id = %s
        """, (chat_id,))
        result = cursor.fetchone()

        if result:
            return True
        return False
    

def delete_booking(chat_id, force=False):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT chat_id, username, name, phone, route, booking_date, seat_number
        FROM bus_bot
        WHERE chat_id = %s
    """, (chat_id,))

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return False, "not_found"

    chat_id, username, name, phone, route, booking_date, seats = row

    if not force:

        now = datetime.now(timezone.utc)

        if booking_date:
            if booking_date.tzinfo is None:
                booking_date = booking_date.replace(tzinfo=timezone.utc)

            diff = booking_date - now

            if diff < timedelta(days=2):
                cur.close()
                conn.close()

                return False, "too_late"

    
    cur.execute("""
        DELETE FROM bus_bot
        WHERE chat_id = %s
    """, (chat_id,))

    conn.commit()
    cur.close()
    conn.close()

    route_text = format_route(route)

    notify_admin(
        f"🗑 БРОНЮВАННЯ СКАСОВАНО\n\n"
        f"👤 ID: {chat_id}\n"
        f"📛 Username: {username}\n"
        f"👤 Name: {name}\n"
        f"📱 Phone: {phone}\n"
        f"🚍 Route: {route_text}\n"
        f"📅 Date: {booking_date}\n"
        f"💺 Seats: {seats}"
    )

    return True, "deleted"


def cleanup_old_bookings():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO archive_clients(
                chat_id, username, name, phone, route, created_at, booking_date, seat_number
        )
        SELECT
            chat_id, username, name, phone, route, created_at, booking_date, seat_number
        FROM bus_bot
        WHERE booking_date::date < CURRENT_DATE
        ON CONFLICT(chat_id) DO NOTHING
    """)

    cur.execute("""
        DELETE FROM bus_bot
        WHERE booking_date::date < CURRENT_DATE
    """)

    conn.commit()
    cur.close()
    conn.close()


def get_all_future_bookings():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT chat_id, route, booking_date, seat_number
        FROM bus_bot
        WHERE booking_date > NOW()
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    bookings = []

    for chat_id, route, booking_date, seats in rows:

        if isinstance(seats, str):
            seats = [int(s) for s in seats.strip("{}").split(",") if s]

        elif isinstance(seats, list):
            seats = [int(s) for s in seats]

        else:
            seats = []

        bookings.append({
            "chat_id": chat_id,
            "route": route,
            "booking_date": booking_date,
            "seats": seats
        })

    return bookings


def search_users(query:str):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT chat_id, username, name, phone, route , booking_date, seat_number
        FROM bus_bot
        WHERE
            CAST(chat_id AS TEXT) ILIKE %s OR
            username ILIKE %s OR
            name ILIKE %s OR
            phone ILIKE %s
        ORDER BY booking_date DESC
        LIMIT 10
    """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
    
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows
    

def get_full_booking(chat_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT chat_id, username, name, phone, route, booking_date, seat_number
        FROM bus_bot
        WHERE chat_id = %s
    """, (chat_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None
    
    return{
        "chat_id": row[0],
        "username": row[1],
        "name": row[2],
        "phone": row[3],
        "route": row[4],
        "booking_date": row[5],
        "seat_number": row[6] or [],
    }


def update_booking(chat_id, **kwargs):

    conn = get_connection()
    cur = conn.cursor()

    fields = []
    values = []

    for key, value in kwargs.items():
        fields.append(f"{key} = %s")
        values.append(value)
    values.append(chat_id)

    query = f"""
        UPDATE bus_bot
        SET {", ".join(fields)}
        WHERE chat_id = %s
    """

    cur.execute(query, values)

    conn.commit()
    cur.close()
    conn.close()

    return True