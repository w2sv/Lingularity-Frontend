from typing import Optional, Dict, Any
import os
import random
import sys
import time

import cursor

from lingularity.backend.metadata import language_metadata
from lingularity.frontend.console.utils.date import date_repr
from lingularity.frontend.console.utils.input_resolution import resolve_input, recurse_on_unresolvable_input
from lingularity.frontend.console.utils.output import clear_screen, centered_print, DEFAULT_VERTICAL_VIEW_OFFSET


def display_starting_screen():
    clear_screen()
    os.system('wmctrl -r :ACTIVE: -b add,maximized_vert,maximized_horz && wmctrl -r :ACTIVE: -N "Lingularity - Acquire Languages the Litboy Way"')
    time.sleep(0.1)

    banner = open(f'{os.getcwd()}/lingularity/frontend/console/resources/banner.txt', 'r').read()
    centered_print(DEFAULT_VERTICAL_VIEW_OFFSET * 2, banner, '\n' * 2)
    centered_print("W2SV", '\n')


def exit_on_missing_internet_connection():
    display_starting_screen()
    centered_print('\nLingularity relies on an internet connection in order to retrieve and store data. Please establish one and restart the program.\n\n')
    cursor.hide()
    time.sleep(5)
    cursor.show()
    sys.exit(0)


def display_additional_information():
    centered_print("Sentence data stemming from the Tatoeba Project to be found at http://www.manythings.org/anki", '\n' * 2)
    centered_print("Note: all requested inputs may be merely entered up to a point which allows for an unambigious identification of the intended choice,")
    centered_print("e.g. 'it' suffices for selecting Italian since there's no other eligible language starting on 'it'", '\n' * 2)


def display_constitution_query(username: str, latest_trained_language: Optional[str]):
    if latest_trained_language is not None and (constitution_query_templates := language_metadata[latest_trained_language]['translations']['constitutionQuery']):
        constitution_queries = map(lambda query: query.replace('{}', username.title()), constitution_query_templates)
    else:
        constitution_queries = map(lambda query: query + f' {username.title()}?', [f"What's up", f"How are you"])

    centered_print(random.choice(list(constitution_queries)), '\n' * 2)


def display_last_session_conclusion(last_session_metrics: Dict[str, Any]):
    centered_print(f"You faced {last_session_metrics['nFacedItems']} {last_session_metrics['language']} {'vocables' if last_session_metrics['trainer'] == 'v' else 'sentences'} during your last session {date_repr(last_session_metrics['date'])}\n\n")


def select_action(actions) -> Optional[str]:
    in_between_indentation = ' ' * 6
    input_message = f"What would you like to do?: {in_between_indentation}Translate (S)entences{in_between_indentation}Train (V)ocabulary{in_between_indentation}(A)dd Vocabulary{in_between_indentation}(C)hange Account\n"
    centered_print(input_message, ' ', end='')

    if (training_selection := resolve_input(input(''), list(actions.keys()))) is None:
        return recurse_on_unresolvable_input(select_action, n_deletion_lines=4)

    clear_screen()
    return training_selection