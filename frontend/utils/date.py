from backend.utils.date import string_2_date, today


def date_repr(date: str) -> str:
    """ Returns:
            'today' if date equals today's date
            'yesterday' if date equaling yesterday's date
            'the {DAY}th of {MONTH} {YEAR}' otherwise

        >>> date_repr(date=str(today))
        'today' """

    converted_date = string_2_date(date)

    if today == converted_date:
        return 'today'
    elif (today - converted_date).days == 1:
        return 'yesterday'
    else:
        return f'the {converted_date.day}th of {converted_date.strftime("%B")} {converted_date.year}'
