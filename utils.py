from zoneinfo import ZoneInfo
from datetime import datetime


def apply_departure_time(date_str:str):

    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=ZoneInfo("Europe/Kyiv"))

    weekday = dt.weekday()

    if weekday in [2,4,6]:
        dt = dt.replace(hour=7, minute=0,second=0,microsecond=0)
    elif weekday in [0,3,5]:
        dt = dt.replace(hour=6, minute=0,second=0,microsecond=0)
    else:
        dt = dt.replace(hour=7, minute=0,second=0,microsecond=0)

    return dt

def format_route(route_value):
    route_map = {
        "ua_md": "🇺🇦 Черкаси → Кишинів 🇲🇩",
        "md_ua": "🇲🇩 Кишинів → Черкаси 🇺🇦"
    }

    return route_map.get(route_value, route_value)


def parce_seats(seats):

    if not seats:
        return []
    
    if isinstance(seats,list):
        return seats
    
    if isinstance(seats,str):
        seats = seats.strip("{}")
        if not seats:
            return []
        return [int(x) for x in seats.split(",")]
    
    return []




