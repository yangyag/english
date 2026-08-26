from datetime import date, datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def get_today() -> date:
    return datetime.now(KST).date()
