import gspread
import os


from google.oauth2.service_account import Credentials
from db_file import get_connection
from log import logger

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")


def get_google_client():
    creds = Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=SCOPES
    )
    return gspread.authorize(creds)


def get_sheet(client, sheet_name="bus_bot"):
    return client.open(sheet_name).sheet1


def fetch_from_postgres():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT chat_id, username, name, phone, route, booking_date, seat_number
        FROM bus_bot
        ORDER BY booking_date DESC
    """)

    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    return [dict(zip(columns, row)) for row in rows]


def export_to_sheets(sheet, data):
    sheet.clear()

    values = [
        ["chat_id", "username", "name", "phone","route", "booking_date", "seat_number"]
    ]


    for row in data:
        values.append([
            str(row.get("chat_id", "")),
            str(row.get("username", "")),
            str(row.get("name", "")),
            str(row.get("phone", "")),
            str(row.get("route", "")),
            str(row.get("booking_date", "")),
            str(row["seat_number"]) if row["seat_number"] else ""
        ])

    sheet.update(
        "A1",
        values,
        value_input_option="RAW"
    )


def sync():

    logger.info("📥 Fetching data from PostgreSQL...")

    data = fetch_from_postgres()

    logger.info(f"📊 Rows fetched: {len(data)}")

    logger.info("🔗 Connecting to Google Sheets...")

    client = get_google_client()
    sheet = get_sheet(client, "bus_bot")

    logger.info("📤 Uploading to Google Sheets...")

    export_to_sheets(sheet, data)

    logger.info("✅ Sync completed successfully!")


