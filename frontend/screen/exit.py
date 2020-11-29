import datetime

from frontend.utils import view
from frontend.screen import _ops


def _day_of_the_month() -> int:
    return int(datetime.datetime.today().strftime('%d'))


@view.creator(title=view.terminal.DEFAULT_TITLE, banner_args=(['lingularity/slant-relief', 'lingularity/sub-zero'][_day_of_the_month() % 2], 'cyan'))
def __call__():
    _ops.display_signum()
    _ops.display_sentence_data_reference()
