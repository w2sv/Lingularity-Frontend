from typing import Optional
import datetime


def datetag_today() -> str:
    return str(datetime.date.today())


def parse_date_from_string(date: str) -> datetime.date:
    return datetime.datetime.strptime(date, '%Y-%m-%d').date()


def day_difference(date: str) -> int:
    return (datetime.date.today() - parse_date_from_string(date)).days


def today_or_yesterday(date: datetime.date) -> Optional[str]:
    today = datetime.datetime.today().date()
    if date == today:
        return 'today'
    elif (today - date).days == 1:
        return 'yesterday'
    else:
        return None
