import re


def normalize_phone(phone: str) -> str:
    phone = re.sub(r"[^\d+]", "", phone)

    if phone.startswith("380"):
        phone = "+" + phone

    elif phone.startswith("0"):
        phone = "+38" + phone

    return phone

def is_valid_ua_phone(phone):
    return bool(re.fullmatch(r"\+380\d{9}", phone))
