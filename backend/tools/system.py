from datetime import datetime
from zoneinfo import ZoneInfo


def get_time(timezone: str | None = None) -> str:
    try:
        now = datetime.now(ZoneInfo(timezone)) if timezone else datetime.now()
    except Exception:
        now = datetime.now()
    return now.strftime("%A, %B %d, %Y at %I:%M %p")
